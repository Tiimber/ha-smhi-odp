"""Renders a 480x480 weather screen image for a wall-mounted device panel.

Produces a hero card, a five-slot forecast row and a 48h temperature
graph as one JPEG, sized for a 480x480 touch panel. Rendering
server-side keeps the device side trivial: it only has to fetch one
image and blit it, which suits small ESP32-class panels that can
decode a JPEG but would struggle to lay out and anti-alias this.

Opt-in per config entry (see the options flow) and driven by the
smhi_odp.generate_device_panel_screen service. Notes on the design:

- Icons are Meteocons ("fill" style, MIT - https://github.com/basmilius/
  weather-icons), bundled as static PNGs under panel_icons/png/,
  rasterised from the SVGs kept alongside them in panel_icons/svg/.
- The background is a single fixed dark navy (#12141a) across every
  weather condition, not a per-condition palette - the icons already
  carry their own color identity.
- Temperature has no native per-hour min/max in SMHI's data (confirmed
  from the live API - only precipitation does), so the graph is a
  single line, and "today/tomorrow min/max" are derived by scanning
  all of that day's hourly entries, same as this integration's
  existing weather.py sensor logic.
"""

import io
import logging
import math
import os
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# ── Layout ──────────────────────────────────────────────────────────
WIDTH = 480
HEIGHT = 480
HERO_HEIGHT = 220
GRID_HEIGHT = 120  # taller than a bare icon/temp/label row - fits a rain% line too
GRAPH_HEIGHT = HEIGHT - HERO_HEIGHT - GRID_HEIGHT  # 140

# ── Colors ──────────────────────────────────────────────────────────
BG_COLOR = (0x12, 0x14, 0x1A)
TEXT_PRIMARY = (255, 255, 255)
TEXT_SECONDARY = (0x9A, 0xA0, 0xAC)
TEXT_DIM = (0x5A, 0x60, 0x6C)
ACCENT = (0xF8, 0xAF, 0x18)  # sampled from the Meteocons sun icon itself
GRID_LINE = (0x2A, 0x2E, 0x38)
RAIN_BAR = (0x3A, 0x7B, 0xD5)

_HERE = os.path.dirname(__file__)
ICON_DIR = os.path.join(_HERE, "panel_icons", "png")
FONT_REGULAR = os.path.join(_HERE, "fonts", "DejaVuSans.ttf")

# ── SMHI symbol code -> Meteocons icon name ────────────────────────
# Mirrors weather.py's CONDITION_CLASSES grouping, extended with
# day/night variants for the two conditions Meteocons distinguishes.
_SYMBOL_GROUPS = {
    "clear": [1],
    "partlycloudy": [2, 3, 4],
    "cloudy": [5, 6],
    "fog": [7],
    "rain": [8, 9, 10, 18, 19, 20],
    "thunder": [11, 21],
    "sleet": [12, 13, 14, 22, 23, 24],
    "snow": [15, 16, 17, 25, 26, 27],
}
_ICON_NAME = {
    "clear": {"day": "clear-day", "night": "clear-night"},
    "partlycloudy": {"day": "partly-cloudy-day", "night": "partly-cloudy-night"},
    "cloudy": {"day": "cloudy", "night": "cloudy"},
    "fog": {"day": "fog", "night": "fog"},
    "rain": {"day": "rain", "night": "rain"},
    "thunder": {"day": "thunderstorms-rain", "night": "thunderstorms-rain"},
    "sleet": {"day": "sleet", "night": "sleet"},
    "snow": {"day": "snow", "night": "snow"},
}

# ── Time-of-day blocks, agreed with the user 2026-08-25 ────────────
# (name, start_hour, end_hour) - Night wraps past midnight (21 -> 06).
BLOCK_DEFS = [
    ("Morning", 6, 10),
    ("Midday", 10, 13),
    ("Afternoon", 13, 17),
    ("Evening", 17, 21),
    ("Night", 21, 6),
]


def _icon_name_for_symbol(symbol, is_daytime):
    variant = "day" if is_daytime else "night"
    for group, codes in _SYMBOL_GROUPS.items():
        if symbol in codes:
            return _ICON_NAME[group][variant]
    return _ICON_NAME["cloudy"][variant]


def _load_icon(name, size):
    path = os.path.join(ICON_DIR, f"{name}.png")
    img = Image.open(path).convert("RGBA")
    return img.resize((size, size), Image.LANCZOS)


def _font(size):
    return ImageFont.truetype(FONT_REGULAR, size)


def _draw_droplet(draw, cx, cy, size, color):
    """A plain water-droplet glyph (round bulb + pointed top) - drawn
    procedurally rather than as another icon asset, since it's just a
    small compact marker for the rain% readouts, not a full weather
    icon."""
    r = size / 2
    bulb_cy = cy + r * 0.25
    draw.polygon(
        [(cx, cy - r), (cx - r * 0.75, bulb_cy - r * 0.2), (cx + r * 0.75, bulb_cy - r * 0.2)],
        fill=color,
    )
    draw.ellipse([cx - r * 0.75, bulb_cy - r * 0.75, cx + r * 0.75, bulb_cy + r * 0.75], fill=color)


def _rain_text(draw, x, y, pct, size, anchor="lm"):
    """Droplet + bare percentage (e.g. "3%", never "03%") - the compact
    rain-risk readout shared by the hero card and each hourly-row slot."""
    color = RAIN_BAR
    _draw_droplet(draw, x, y, size, color)
    f = _font(int(size * 0.9))
    draw.text((x + size, y), f"{pct:.0f}%", font=f, fill=TEXT_SECONDARY, anchor=anchor)


# ── Parsing the raw SMHI timeSeries ─────────────────────────────────


def _entries(coordinator_data):
    """Return (local_datetime, data_dict) pairs, sorted, for every entry."""
    out = []
    for entry in coordinator_data.get("timeSeries", []):
        time_str = entry.get("time") or entry.get("validTime")
        if not time_str:
            continue
        parsed = dt_util.parse_datetime(time_str)
        if not parsed:
            continue
        out.append((dt_util.as_local(parsed), entry.get("data", {})))
    out.sort(key=lambda pair: pair[0])
    return out


def _daily_min_max(entries, date):
    temps = [d.get("air_temperature") for dt, d in entries if dt.date() == date]
    temps = [t for t in temps if t is not None]
    if not temps:
        return None, None
    return min(temps), max(temps)


def _dominant_symbol(entries, date):
    """Most common symbol code for a given date (used for a day's icon)."""
    counts = {}
    for dt, d in entries:
        if dt.date() != date:
            continue
        sym = d.get("symbol_code")
        if sym is not None:
            counts[sym] = counts.get(sym, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def _nearest_entry(entries, target):
    """Entry whose time is closest to target (used for a single-hour lookup)."""
    if not entries:
        return None
    return min(entries, key=lambda pair: abs((pair[0] - target).total_seconds()))


# ── The "smart" hourly row (see the phase1 plan for the algorithm) ──


def _block_bounds(date, start_hour, end_hour):
    start = datetime.combine(date, datetime.min.time()).replace(
        hour=start_hour, tzinfo=dt_util.DEFAULT_TIME_ZONE
    )
    if end_hour <= start_hour:  # Night wraps to next day
        end = start + timedelta(hours=(24 - start_hour) + end_hour)
    else:
        end = start.replace(hour=end_hour)
    return start, end


def _block_occurrences(now):
    """Concrete (name, start, end) block occurrences around `now`.

    BLOCK_DEFS tile the clock exactly (Night's 21->06 wrap hands over to
    the next day's Morning at 06:00), so sorting these by start time
    gives a gap-free, non-overlapping timeline to walk forward along.
    """
    occurrences = []
    for day_offset in range(-1, 4):
        d = now.date() + timedelta(days=day_offset)
        for name, sh, eh in BLOCK_DEFS:
            start, end = _block_bounds(d, sh, eh)
            occurrences.append((name, start, end))
    occurrences.sort(key=lambda o: o[1])
    return occurrences


def _blocks_after(now, count):
    """The `count` block occurrences following the one containing `now`."""
    occurrences = _block_occurrences(now)
    for i, (_, start, end) in enumerate(occurrences):
        if start <= now < end:
            return occurrences[i + 1 : i + 1 + count]
    return occurrences[:count]


def _aggregate_period(entries, start, end):
    """Average/extreme values across one period, or None if no data."""
    period = [d for dt, d in entries if start <= dt < end]
    temps = [d.get("air_temperature") for d in period if d.get("air_temperature") is not None]
    rains = [
        d.get("probability_of_precipitation")
        for d in period
        if d.get("probability_of_precipitation") is not None
    ]
    symbols = [d.get("symbol_code") for d in period if d.get("symbol_code") is not None]
    if not temps:
        return None
    return {
        "temp_avg": sum(temps) / len(temps),
        "rain_avg": sum(rains) / len(rains) if rains else 0,
        "symbol": max(set(symbols), key=symbols.count) if symbols else None,
    }


def _tomorrow_summary(now, entries):
    """Whole-of-tomorrow item: temperature span + worst-case rain."""
    date = now.date() + timedelta(days=1)
    temps = [
        d.get("air_temperature")
        for dt, d in entries
        if dt.date() == date and d.get("air_temperature") is not None
    ]
    rains = [
        d.get("probability_of_precipitation")
        for dt, d in entries
        if dt.date() == date and d.get("probability_of_precipitation") is not None
    ]
    if not temps:
        return None
    return {
        "kind": "summary",
        "label": "Tomorrow",
        "tmin": min(temps),
        "tmax": max(temps),
        "rain_pct": max(rains) if rains else 0,
        "symbol": _dominant_symbol(entries, date),
    }


def build_hourly_row(now, entries):
    """The five-slot row under the hero card (structure agreed 2026-08-25).

    Slots 1-2 are always the next two individual hours (exact values for
    that hour). Slots 3-4 are always the next two time-of-day blocks
    (BLOCK_DEFS), shown as that period's *average* temperature and rain
    chance. Slot 5 depends on how far slot 4 already reaches: if slot 4
    is still entirely within today, slot 5 becomes a whole-of-tomorrow
    summary (temperature span + worst-case rain); if slot 4 already
    covers part of tomorrow, another block follows instead.

    Item shapes:
      {"kind": "hour",    "time": dt,   "temp": float, "rain_pct": float, "symbol": int}
      {"kind": "block",   "name": str,  "temp": float, "rain_pct": float, "symbol": int}
      {"kind": "summary", "label": str, "tmin": float, "tmax": float, "rain_pct": float, "symbol": int}
    """
    row = []

    for offset in (1, 2):
        target = (now + timedelta(hours=offset)).replace(minute=0, second=0, microsecond=0)
        entry = _nearest_entry(entries, target)
        if entry:
            row.append(
                {
                    "kind": "hour",
                    "time": target,
                    "temp": entry[1].get("air_temperature"),
                    "rain_pct": entry[1].get("probability_of_precipitation") or 0,
                    "symbol": entry[1].get("symbol_code"),
                }
            )

    blocks = _blocks_after(now, 3)
    end_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    for index, (name, start, end) in enumerate(blocks):
        # index 0/1 are slots 3/4; index 2 is slot 5, which only stays a
        # block when slot 4 already ran into tomorrow.
        if index == 2:
            slot4_end = blocks[1][2] if len(blocks) > 1 else None
            if slot4_end is not None and slot4_end <= end_of_today:
                summary = _tomorrow_summary(now, entries)
                if summary:
                    row.append(summary)
                continue

        aggregate = _aggregate_period(entries, start, end)
        if aggregate:
            row.append(
                {
                    "kind": "block",
                    "name": name,
                    "temp": aggregate["temp_avg"],
                    "rain_pct": aggregate["rain_avg"],
                    "symbol": aggregate["symbol"],
                }
            )

    return row


# ── The 48h graph series ────────────────────────────────────────────


def build_graph_series(now, entries, history_points=None):
    """Hourly (interpolated) temp from start-of-today through end-of-tomorrow.

    The pre-"now" portion (today's already-elapsed hours) comes from
    real recorder history (history_points: a list of (local_datetime,
    temperature) pairs for the weather entity, fetched by the caller -
    see __init__.py), not SMHI's forecast, which never has data for
    hours that already passed. The post-"now" portion comes from the
    SMHI forecast entries as before. Always a fixed 48h span.

    Returns (hours, temps, divider_hour, now_hour) where hours is
    0..47 (0 = today 00:00), divider_hour=24 (always, since the span
    always starts at today's midnight), and now_hour is where to draw
    the current-time marker.
    """
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end = today_midnight + timedelta(days=2)
    now_hour = (now - today_midnight).total_seconds() / 3600.0

    known = []
    for pt_dt, temp in history_points or []:
        if today_midnight <= pt_dt < tomorrow_end and temp is not None:
            known.append(((pt_dt - today_midnight).total_seconds() / 3600.0, temp))
    for dt, d in entries:
        temp = d.get("air_temperature")
        if today_midnight <= dt < tomorrow_end and temp is not None:
            known.append(((dt - today_midnight).total_seconds() / 3600.0, temp))
    known.sort(key=lambda k: k[0])

    if not known:
        return [], [], 24.0, now_hour

    def interp(h):
        """None (not extrapolated) when h falls outside the known range -
        e.g. today's hours before whatever history is available. A flat
        fabricated line looks like real data when it isn't; leaving a
        gap doesn't."""
        before = [k for k in known if k[0] <= h]
        after = [k for k in known if k[0] >= h]
        if before and after:
            if before[-1][0] == after[0][0]:
                return before[-1][1]
            h0, v0 = before[-1]
            h1, v1 = after[0]
            frac = (h - h0) / (h1 - h0)
            return v0 + (v1 - v0) * frac
        return None

    hours = list(range(48))
    temps = [interp(h) for h in hours]
    return hours, temps, 24.0, now_hour


def _moving_average(values, window=3, passes=2):
    """Light smoothing on the raw hourly values themselves, before
    spline-fitting - see the comment at the call site for why both are
    needed. Edges are clamped (padded with the nearest real value)
    rather than wrapped or dropped, so the line still starts/ends at
    close to the real first/last temperature."""
    if len(values) < window:
        return list(values)
    half = window // 2
    result = list(values)
    for _ in range(passes):
        padded = [result[0]] * half + result + [result[-1]] * half
        result = [sum(padded[i : i + window]) / window for i in range(len(result))]
    return result


def _catmull_rom_smooth(points, samples_per_segment=8):
    """Smooth a polyline by sampling a Catmull-Rom spline through it.

    Pure-Python, no scipy/numpy dependency - just enough to turn the
    hourly straight-line-segment polyline into a visually smooth curve.
    """
    if len(points) < 3:
        return points

    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for s in range(samples_per_segment):
            t = s / samples_per_segment
            t2, t3 = t * t, t * t * t
            x = 0.5 * (
                2 * p1[0]
                + (-p0[0] + p2[0]) * t
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                2 * p1[1]
                + (-p0[1] + p2[1]) * t
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            out.append((x, y))
    out.append(points[-1])
    return out


# ── Drawing ─────────────────────────────────────────────────────────


def _draw_hero(draw, img, entries, now, is_daytime):
    """Just current temp + risk of rain - no H/L (that's covered by the
    hourly-row's blocks/Today-Tomorrow summary already, and per user
    feedback the hero didn't need to duplicate it)."""
    current = _nearest_entry(entries, now)
    temp = current[1].get("air_temperature") if current else None
    symbol = current[1].get("symbol_code") if current else None
    rain_pct = (current[1].get("probability_of_precipitation") or 0) if current else 0

    icon_name = _icon_name_for_symbol(symbol, is_daytime) if symbol is not None else "cloudy"
    icon = _load_icon(icon_name, 200)
    img.paste(icon, (20, 15), icon)

    right_x = WIDTH - 30
    temp_center_x = right_x - 60  # fallback if there's no temperature to measure
    if temp is not None:
        f_temp = _font(96)
        text = f"{temp:.0f}°"
        w = draw.textlength(text, font=f_temp)
        draw.text((right_x - w, 25), text, font=f_temp, fill=TEXT_PRIMARY)
        temp_center_x = right_x - w / 2

    # compact rain readout: droplet + bare "%" - no label, matching the
    # per-hourly-row-slot version, but larger and centered under the
    # temperature rather than right-aligned with it
    droplet_size = 28
    text_w = draw.textlength(f"{rain_pct:.0f}%", font=_font(int(droplet_size * 0.9)))
    total_w = droplet_size + text_w
    _rain_text(draw, temp_center_x - total_w / 2, 158, rain_pct, droplet_size, anchor="lm")


def _item_is_daytime(item):
    """Rough day/night check per row item - good enough for icon choice.

    Uses the same 06:00/21:00 boundary as the Morning/Night blocks
    rather than a real sunrise/sunset calc, to stay consistent with how
    the row already reasons about "day" for block purposes.
    """
    if item["kind"] == "hour":
        return 6 <= item["time"].hour < 21
    if item["kind"] == "block":
        return item["name"] != "Night"
    return True  # "summary" (Today/Tomorrow) - generic daytime icon


def _draw_hourly_row(draw, img, row):
    y0 = HERO_HEIGHT
    n = len(row) or 1
    slot_w = WIDTH / n
    f_temp = _font(24)
    f_label = _font(18)

    for i, item in enumerate(row):
        cx = int(slot_w * i + slot_w / 2)
        icon_symbol = item.get("symbol")
        icon_name = (
            _icon_name_for_symbol(icon_symbol, _item_is_daytime(item))
            if icon_symbol is not None
            else "cloudy"
        )
        icon = _load_icon(icon_name, 36)
        img.paste(icon, (cx - 18, y0 + 2), icon)

        if item["kind"] == "hour":
            label = item["time"].strftime("%H:%M")
            temp_text = f"{item['temp']:.0f}°" if item.get("temp") is not None else "--"
        elif item["kind"] == "block":
            # blocks show that period's average, not its range
            label = item["name"]
            temp_text = f"{item['temp']:.0f}°"
        else:
            # the whole-of-tomorrow summary keeps a span
            label = item["label"]
            temp_text = f"{item['tmin']:.0f}-{item['tmax']:.0f}°"

        w = draw.textlength(temp_text, font=f_temp)
        draw.text((cx - w / 2, y0 + 42), temp_text, font=f_temp, fill=TEXT_PRIMARY)

        # rain% sits directly under the temperature, with the time/period
        # label last - and a clear gap between the two so they don't read
        # as one block of text
        rain_pct = item.get("rain_pct", 0)
        droplet_size = 14
        rain_text_w = draw.textlength(f"{rain_pct:.0f}%", font=_font(int(droplet_size * 0.9)))
        rain_total_w = droplet_size + rain_text_w
        _rain_text(draw, cx - rain_total_w / 2, y0 + 80, rain_pct, droplet_size, anchor="lm")

        w = draw.textlength(label, font=f_label)
        draw.text((cx - w / 2, y0 + 96), label, font=f_label, fill=TEXT_SECONDARY)


def _draw_graph(draw, hours, temps, divider_hour, now_hour):
    y0 = HERO_HEIGHT + GRID_HEIGHT
    pad_l, pad_r, pad_t, pad_b = 10, 10, 12, 12
    plot_h = GRAPH_HEIGHT - pad_t - pad_b  # plot_w depends on the axis-label gutter, below

    valid = [(h, t) for h, t in zip(hours, temps) if t is not None]
    if not valid:
        return

    last_hour = hours[-1]
    # Round the y-axis to clean 5-degree steps rather than the raw
    # min/max, so gridlines land on round numbers.
    valid_temps = [t for _, t in valid]
    grid_min = math.floor(min(valid_temps) / 5) * 5
    grid_max = math.ceil(max(valid_temps) / 5) * 5
    if grid_max == grid_min:
        grid_max += 5
    span = grid_max - grid_min

    # Reserve a left gutter wide enough for the axis labels, so the plot
    # (and the temperature line) starts to their right instead of running
    # across the top of them.
    f_grid = _font(16)
    axis_labels = []
    step = grid_min
    while step <= grid_max:
        axis_labels.append(f"{step:.0f}°")
        step += 5
    axis_w = max(draw.textlength(t, font=f_grid) for t in axis_labels) + 6
    plot_l = pad_l + axis_w
    plot_w = WIDTH - plot_l - pad_r

    def x_px(h):
        return plot_l + (h / last_hour) * plot_w

    def y_px(t):
        return y0 + pad_t + (1 - (t - grid_min) / span) * plot_h

    # 5-degree horizontal gridlines with labels
    for i, text in enumerate(axis_labels):
        value = grid_min + i * 5
        gy = y_px(value)
        draw.line([(plot_l, gy), (WIDTH - pad_r, gy)], fill=GRID_LINE, width=1)
        draw.text((pad_l, gy), text, font=f_grid, fill=TEXT_DIM, anchor="lm")

    # today/tomorrow divider
    if 0 <= divider_hour <= last_hour:
        xm = x_px(divider_hour)
        draw.line([(xm, y0 + pad_t), (xm, y0 + pad_t + plot_h)], fill=GRID_LINE, width=1)

    # smoothed temperature line (only over the contiguous known stretch -
    # see build_graph_series: gaps stay blank rather than fabricated).
    # A light moving-average pass takes the small hour-to-hour noise out
    # first - a spline through noisy points still looks noisy, just with
    # rounded corners - then a denser Catmull-Rom pass turns that into an
    # actually smooth curve.
    smoothed_temps = _moving_average([t for _, t in valid], window=5, passes=3)
    raw_points = [(x_px(h), y_px(t)) for (h, _), t in zip(valid, smoothed_temps)]
    smooth_points = _catmull_rom_smooth(raw_points, samples_per_segment=16)
    draw.line(smooth_points, fill=TEXT_PRIMARY, width=3, joint="curve")

    # current-time marker
    marker_temp = _interp_temps(valid, now_hour)
    if marker_temp is not None:
        now_x, now_y = x_px(now_hour), y_px(marker_temp)
        draw.ellipse([now_x - 5, now_y - 5, now_x + 5, now_y + 5], fill=ACCENT)


def _interp_temps(valid, h):
    """Linear lookup into the (hour, temp) pairs with no gaps, for a
    marker position that may fall between two integer hours."""
    if not valid:
        return None
    if h <= valid[0][0]:
        return valid[0][1]
    if h >= valid[-1][0]:
        return valid[-1][1]
    for (h0, v0), (h1, v1) in zip(valid, valid[1:]):
        if h0 <= h <= h1:
            frac = (h - h0) / (h1 - h0) if h1 != h0 else 0
            return v0 + (v1 - v0) * frac
    return None


def generate_weather_screen(coordinator_data, is_daytime=True, history_points=None):
    """Render the full weather screen. Returns JPEG bytes.

    history_points: optional list of (local_datetime, temperature)
    pairs from the weather entity's recorder history, covering today's
    already-elapsed hours - see __init__.py's handler, which fetches
    this via HA's recorder before calling here. Without it, the graph
    simply has no line before "now" (today's earlier hours stay blank
    rather than fabricated).
    """
    now = dt_util.now()
    entries = _entries(coordinator_data)
    if not entries:
        raise ValueError("No SMHI timeSeries data available to render")

    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    _draw_hero(draw, img, entries, now, is_daytime)

    row = build_hourly_row(now, entries)
    _draw_hourly_row(draw, img, row)

    hours, temps, divider_hour, now_hour = build_graph_series(now, entries, history_points)
    _draw_graph(draw, hours, temps, divider_hour, now_hour)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()
