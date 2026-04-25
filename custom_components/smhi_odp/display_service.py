"""Display service for generating Ulanzi weather GIFs."""
import io
import logging
from datetime import datetime, timedelta
from typing import Any

from PIL import Image, ImageDraw, ImageFont
from homeassistant.util import dt as dt_util

from .weather_icons import get_icon_pixels, ICONS

_LOGGER = logging.getLogger(__name__)

# Display dimensions
DISPLAY_WIDTH = 32
DISPLAY_HEIGHT = 8

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BLUE_COLD = (100, 150, 255)
BLUE = (50, 150, 255)
GREEN = (50, 255, 100)
YELLOW = (255, 200, 0)
ORANGE = (255, 150, 0)
RED = (255, 50, 50)
RAIN_BLUE = (0, 100, 255)
GRAY = (150, 150, 150)

# Font simulation - for 8x8 display we'll use pixel-perfect rendering
# 3x5 font for text, 5x7 for numbers
SMALL_CHAR_WIDTH = 4  # 3px + 1px spacing
LARGE_CHAR_WIDTH = 6  # 5px + 1px spacing


class WeatherDisplayService:
    """Service to generate weather display GIFs."""

    def __init__(self):
        """Initialize the display service."""
        self._cache = {}
        self._cache_hashes = {}

    def _get_temp_color(self, temp):
        """Get color for temperature value."""
        if temp < 0:
            return BLUE_COLD
        elif temp < 10:
            return BLUE
        elif temp < 20:
            return GREEN
        elif temp < 30:
            return ORANGE
        else:
            return RED

    def _draw_icon(self, draw, image, x, y, icon_pixels):
        """Draw an 8x8 icon at the specified position."""
        for row_idx, row in enumerate(icon_pixels):
            for col_idx, pixel in enumerate(row):
                if pixel != 0:  # 0 is transparent
                    px = x + col_idx
                    py = y + row_idx
                    if 0 <= px < image.width and 0 <= py < image.height:
                        image.putpixel((px, py), pixel)

    def _draw_text_3x5(self, draw, image, x, y, text, color):
        """Draw text using a simple 3x5 pixel font."""
        # Simple 3x5 bitmap font for basic characters
        font_map = {
            '0': [[1,1,1],[1,0,1],[1,0,1],[1,0,1],[1,1,1]],
            '1': [[0,1,0],[1,1,0],[0,1,0],[0,1,0],[1,1,1]],
            '2': [[1,1,1],[0,0,1],[1,1,1],[1,0,0],[1,1,1]],
            '3': [[1,1,1],[0,0,1],[1,1,1],[0,0,1],[1,1,1]],
            '4': [[1,0,1],[1,0,1],[1,1,1],[0,0,1],[0,0,1]],
            '5': [[1,1,1],[1,0,0],[1,1,1],[0,0,1],[1,1,1]],
            '6': [[1,1,1],[1,0,0],[1,1,1],[1,0,1],[1,1,1]],
            '7': [[1,1,1],[0,0,1],[0,0,1],[0,0,1],[0,0,1]],
            '8': [[1,1,1],[1,0,1],[1,1,1],[1,0,1],[1,1,1]],
            '9': [[1,1,1],[1,0,1],[1,1,1],[0,0,1],[1,1,1]],
            '°': [[1,1,0],[1,1,0],[0,0,0],[0,0,0],[0,0,0]],
            '-': [[0,0,0],[0,0,0],[1,1,1],[0,0,0],[0,0,0]],
            'M': [[1,0,1],[1,1,1],[1,1,1],[1,0,1],[1,0,1]],
            'O': [[1,1,1],[1,0,1],[1,0,1],[1,0,1],[1,1,1]],
            'R': [[1,1,0],[1,0,1],[1,1,0],[1,0,1],[1,0,1]],
            'N': [[1,0,1],[1,1,1],[1,1,1],[1,0,1],[1,0,1]],
            'A': [[0,1,0],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
            'F': [[1,1,1],[1,0,0],[1,1,0],[1,0,0],[1,0,0]],
            'T': [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[0,1,0]],
            'E': [[1,1,1],[1,0,0],[1,1,0],[1,0,0],[1,1,1]],
            'V': [[1,0,1],[1,0,1],[1,0,1],[1,0,1],[0,1,0]],
            'W': [[1,0,1],[1,0,1],[1,1,1],[1,1,1],[1,0,1]],
            'D': [[1,1,0],[1,0,1],[1,0,1],[1,0,1],[1,1,0]],
            'U': [[1,0,1],[1,0,1],[1,0,1],[1,0,1],[1,1,1]],
            'H': [[1,0,1],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
            'S': [[1,1,1],[1,0,0],[1,1,1],[0,0,1],[1,1,1]],
            'I': [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[1,1,1]],
            ' ': [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]],
            'm': [[0,0,0],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
            '/': [[0,0,1],[0,0,1],[0,1,0],[1,0,0],[1,0,0]],
            's': [[0,0,0],[1,1,1],[1,0,0],[0,0,1],[1,1,1]],
        }
        
        current_x = x
        for char in text.upper():
            if char in font_map:
                bitmap = font_map[char]
                for row_idx, row in enumerate(bitmap):
                    for col_idx, pixel in enumerate(row):
                        if pixel:
                            px = current_x + col_idx
                            py = y + row_idx
                            if 0 <= px < image.width and 0 <= py < image.height:
                                image.putpixel((px, py), color)
                current_x += 4  # 3px char + 1px spacing
        
        return current_x

    def _draw_border(self, draw, image, x, y, width, height, color=WHITE):
        """Draw a border rectangle."""
        # Top line
        for i in range(width):
            if 0 <= x + i < image.width and 0 <= y < image.height:
                image.putpixel((x + i, y), color)
        # Bottom line
        for i in range(width):
            if 0 <= x + i < image.width and 0 <= y + height - 1 < image.height:
                image.putpixel((x + i, y + height - 1), color)
        # Left line
        for i in range(height):
            if 0 <= x < image.width and 0 <= y + i < image.height:
                image.putpixel((x, y + i), color)
        # Right line
        for i in range(height):
            if 0 <= x + width - 1 < image.width and 0 <= y + i < image.height:
                image.putpixel((x + width - 1, y + i), color)

    def _create_frame(self, bg_color=BLACK):
        """Create a blank frame."""
        return Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), bg_color)

    def _create_scrolling_gif(self, frames, frame_duration=100):
        """Create a GIF from frames with scrolling animation."""
        if not frames:
            return None
        
        # Save as GIF in memory
        output = io.BytesIO()
        frames[0].save(
            output,
            format='GIF',
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration,
            loop=0,  # Infinite loop
            optimize=False
        )
        output.seek(0)
        return output.getvalue()

    def _calculate_data_hash(self, data):
        """Calculate a hash for weather data to detect changes."""
        # Simple hash based on relevant data
        return hash(str(data))

    async def generate_today_gif(self, coordinator, entry) -> bytes:
        """Generate the 'Today' GIF showing hourly forecast (05-22)."""
        cache_key = f"{entry.entry_id}_today"
        data_hash = self._calculate_data_hash(coordinator.data)
        
        # Check cache
        if cache_key in self._cache and self._cache_hashes.get(cache_key) == data_hash:
            _LOGGER.debug("Returning cached Today GIF")
            return self._cache[cache_key]
        
        _LOGGER.info("Generating new Today GIF")
        
        # Parse weather data
        time_series = coordinator.data.get("timeSeries", [])
        now_local = dt_util.now()
        current_hour = now_local.hour
        
        # Filter hours 5-22 for today
        hourly_data = []
        for entry_data in time_series:
            time_str = entry_data.get("time") or entry_data.get("validTime")
            if not time_str:
                continue
            
            entry_time = dt_util.parse_datetime(time_str)
            if not entry_time:
                continue
            
            entry_time_local = dt_util.as_local(entry_time)
            
            # Only today, hours 5-22
            if entry_time_local.date() == now_local.date():
                hour = entry_time_local.hour
                if 5 <= hour <= 22:
                    hourly_data.append({
                        "hour": hour,
                        "time": entry_time_local,
                        "data": entry_data.get("data") or entry_data.get("parameters", [])
                    })
        
        if not hourly_data:
            _LOGGER.warning("No hourly data found for today")
            return self._create_error_gif("NO DATA")
        
        # Create frames
        frames = self._generate_hourly_scroll_frames(hourly_data, current_hour)
        
        # Generate GIF
        gif_bytes = self._create_scrolling_gif(frames, frame_duration=120)
        
        # Cache result
        self._cache[cache_key] = gif_bytes
        self._cache_hashes[cache_key] = data_hash
        
        return gif_bytes

    def _generate_hourly_scroll_frames(self, hourly_data, current_hour):
        """Generate scrolling frames for hourly data."""
        frames = []
        
        # Calculate total width needed
        # Each hour block: 8px icon + 2px space + ~12px text = 22px per hour
        hour_block_width = 22
        total_width = len(hourly_data) * hour_block_width
        
        # Create a wide canvas
        canvas_width = max(total_width, DISPLAY_WIDTH)
        
        # Generate scroll positions (scroll from right to left)
        scroll_positions = []
        if canvas_width > DISPLAY_WIDTH:
            # Scroll through all data
            for offset in range(0, canvas_width - DISPLAY_WIDTH + 1, 2):
                scroll_positions.append(offset)
            # Hold at end for a moment
            for _ in range(10):
                scroll_positions.append(canvas_width - DISPLAY_WIDTH)
        else:
            scroll_positions = [0]  # No scroll needed
        
        # Draw all hourly blocks on the wide canvas
        wide_canvas = Image.new('RGB', (canvas_width, DISPLAY_HEIGHT), BLACK)
        draw = ImageDraw.Draw(wide_canvas)
        
        x_pos = 0
        for hour_info in hourly_data:
            hour = hour_info["hour"]
            data_params = hour_info["data"]
            
            # Extract data
            temp = self._get_parameter(data_params, "air_temperature", "t")
            precip = self._get_parameter(data_params, "precipitation_amount_median", "pmedian")
            symbol = self._get_parameter(data_params, "symbol_code", "Wsymb2")
            wind_speed = self._get_parameter(data_params, "wind_speed", "ws")
            
            # Draw icon
            if symbol:
                icon_pixels = get_icon_pixels(int(symbol))
                self._draw_icon(draw, wide_canvas, x_pos, 0, icon_pixels)
            
            # Check if this is current hour
            is_current = (hour == current_hour)
            
            # Draw border if current hour
            if is_current:
                self._draw_border(draw, wide_canvas, x_pos, 0, hour_block_width - 2, DISPLAY_HEIGHT, YELLOW)
            
            # Draw temperature
            if temp is not None:
                temp_color = self._get_temp_color(temp)
                temp_text = f"{int(temp)}"
                self._draw_text_3x5(draw, wide_canvas, x_pos + 9, 0, temp_text, temp_color)
            
            # Draw precipitation if > 0
            if precip and precip > 0:
                precip_text = f"{int(precip)}mm"
                self._draw_text_3x5(draw, wide_canvas, x_pos + 9, 5, precip_text[:3], RAIN_BLUE)
            
            # Draw hour number at bottom (if space)
            # hour_text = f"{hour:02d}"
            # self._draw_text_3x5(draw, wide_canvas, x_pos + 10, 6, hour_text, GRAY)
            
            x_pos += hour_block_width
        
        # Create frames by sliding the viewport
        for offset in scroll_positions:
            frame = wide_canvas.crop((offset, 0, offset + DISPLAY_WIDTH, DISPLAY_HEIGHT))
            frames.append(frame)
        
        return frames

    def _get_parameter(self, parameters, name, fallback_name=None):
        """Extract parameter value from SMHI data.
        
        Supports both formats:
        - Array format: [{"name": "t", "values": [10.5]}]
        - Object format: {"air_temperature": 10.5}
        """
        # Check if it's an object (dict) - snow1g API format
        if isinstance(parameters, dict):
            # Try primary name first, then fallback
            if name in parameters:
                return parameters[name]
            if fallback_name and fallback_name in parameters:
                return parameters[fallback_name]
            return None
        
        # Otherwise assume it's an array - old format
        for param in parameters:
            if param.get("name") == name or (fallback_name and param.get("name") == fallback_name):
                values = param.get("values")
                if values and len(values) > 0:
                    return values[0]
        return None

    def _create_error_gif(self, message):
        """Create a simple error message GIF."""
        frame = self._create_frame()
        draw = ImageDraw.Draw(frame)
        self._draw_text_3x5(draw, frame, 2, 2, message[:8], RED)
        
        output = io.BytesIO()
        frame.save(output, format='GIF')
        output.seek(0)
        return output.getvalue()

    async def generate_tomorrow_gif(self, coordinator, entry) -> bytes:
        """Generate the 'Tomorrow' GIF showing time blocks."""
        cache_key = f"{entry.entry_id}_tomorrow"
        data_hash = self._calculate_data_hash(coordinator.data)
        
        if cache_key in self._cache and self._cache_hashes.get(cache_key) == data_hash:
            _LOGGER.debug("Returning cached Tomorrow GIF")
            return self._cache[cache_key]
        
        _LOGGER.info("Generating new Tomorrow GIF")
        
        # Parse data for tomorrow
        time_series = coordinator.data.get("timeSeries", [])
        now_local = dt_util.now()
        tomorrow_date = (now_local + timedelta(days=1)).date()
        
        # Collect tomorrow's data
        tomorrow_data = []
        for entry_data in time_series:
            time_str = entry_data.get("time") or entry_data.get("validTime")
            if not time_str:
                continue
            
            entry_time = dt_util.parse_datetime(time_str)
            if not entry_time:
                continue
            
            entry_time_local = dt_util.as_local(entry_time)
            
            if entry_time_local.date() == tomorrow_date:
                tomorrow_data.append({
                    "hour": entry_time_local.hour,
                    "data": entry_data.get("data") or entry_data.get("parameters", [])
                })
        
        if not tomorrow_data:
            _LOGGER.warning("No data found for tomorrow")
            return self._create_error_gif("NO DATA")
        
        # Aggregate into time blocks
        blocks = self._aggregate_time_blocks(tomorrow_data)
        
        # Generate frames
        frames = self._generate_block_scroll_frames(blocks, "TOMORROW")
        
        gif_bytes = self._create_scrolling_gif(frames, frame_duration=120)
        
        self._cache[cache_key] = gif_bytes
        self._cache_hashes[cache_key] = data_hash
        
        return gif_bytes

    def _aggregate_time_blocks(self, hourly_data):
        """Aggregate hourly data into morning/afternoon/evening blocks."""
        _LOGGER.info(f"Aggregating {len(hourly_data)} hours of data")
        
        blocks = {
            "MORN": {"hours": [], "max_temp": -999, "total_precip": 0, "symbols": []},
            "AFT": {"hours": [], "max_temp": -999, "total_precip": 0, "symbols": []},
            "EVE": {"hours": [], "max_temp": -999, "total_precip": 0, "symbols": []},
        }
        
        for hour_data in hourly_data:
            hour = hour_data["hour"]
            params = hour_data["data"]
            
            _LOGGER.debug(f"Hour {hour}: {len(params)} parameters")
            
            # Determine block
            if 5 <= hour < 12:
                block_key = "MORN"
            elif 12 <= hour < 18:
                block_key = "AFT"
            elif 18 <= hour <= 22:
                block_key = "EVE"
            else:
                continue  # Skip night hours
            
            # Extract values
            temp = self._get_parameter(params, "air_temperature", "t")
            precip = self._get_parameter(params, "precipitation_amount_median", "pmedian")
            symbol = self._get_parameter(params, "symbol_code", "Wsymb2")
            
            _LOGGER.debug(f"Hour {hour} ({block_key}): temp={temp}, precip={precip}, symbol={symbol}")
            
            if temp is not None:
                blocks[block_key]["max_temp"] = max(blocks[block_key]["max_temp"], temp)
            if precip is not None:
                blocks[block_key]["total_precip"] += precip
            if symbol is not None:
                blocks[block_key]["symbols"].append(int(symbol))
        
        # Determine most severe symbol for each block
        for block in blocks.values():
            if block["symbols"]:
                block["symbol"] = self._get_most_severe_symbol(block["symbols"])
        
        _LOGGER.info(f"Aggregated blocks: MORN={blocks['MORN']['max_temp']}, AFT={blocks['AFT']['max_temp']}, EVE={blocks['EVE']['max_temp']}")
        
        return blocks

    def _get_most_severe_symbol(self, symbols):
        """Get the most severe weather symbol from a list."""
        # Severity ranking (higher = more severe)
        severity_map = {
            11: 10, 21: 10,  # Thunder
            10: 9, 20: 9,    # Heavy rain
            17: 8, 27: 8,    # Heavy snow
            16: 7, 26: 7,    # Moderate snow
            15: 6, 25: 6,    # Light snow
            14: 5, 24: 5,    # Heavy sleet
            13: 4, 23: 4,    # Moderate sleet
            12: 3, 22: 3,    # Light sleet
            9: 2, 19: 2,     # Moderate rain
            8: 1, 18: 1,     # Light rain
            7: 0,            # Fog
            5: -1, 6: -1,    # Cloudy
            3: -2, 4: -2,    # Partly cloudy
            1: -3, 2: -3,    # Clear
        }
        
        most_severe = max(symbols, key=lambda s: severity_map.get(s, -999))
        return most_severe

    def _generate_block_scroll_frames(self, blocks, title):
        """Generate scrolling frames for time block data."""
        frames = []
        
        # Calculate width: title + 3 blocks
        # Title: ~32px, each block: ~28px
        block_width = 28
        title_width = 32
        total_width = title_width + (block_width * 3)
        
        canvas_width = max(total_width, DISPLAY_WIDTH)
        wide_canvas = Image.new('RGB', (canvas_width, DISPLAY_HEIGHT), BLACK)
        draw = ImageDraw.Draw(wide_canvas)
        
        # Draw title
        self._draw_text_3x5(draw, wide_canvas, 2, 2, title[:8], WHITE)
        
        x_pos = title_width
        for block_name, block_data in [("MORN", blocks["MORN"]), ("AFT", blocks["AFT"]), ("EVE", blocks["EVE"])]:
            _LOGGER.info(f"Drawing block {block_name}: max_temp={block_data.get('max_temp')}, symbol={block_data.get('symbol')}, precip={block_data.get('total_precip')}")
            
            if block_data["max_temp"] == -999:
                continue  # No data for this block
            
            # Draw icon
            if "symbol" in block_data and block_data["symbol"] is not None:
                icon_pixels = get_icon_pixels(block_data["symbol"])
                _LOGGER.info(f"Drawing icon for symbol {block_data['symbol']} at x={x_pos}")
                self._draw_icon(draw, wide_canvas, x_pos, 0, icon_pixels)
            
            # Draw temperature
            temp = block_data["max_temp"]
            temp_color = self._get_temp_color(temp)
            temp_text = f"{int(temp)}"
            _LOGGER.info(f"Drawing temperature {temp_text} at x={x_pos + 9}")
            self._draw_text_3x5(draw, wide_canvas, x_pos + 9, 0, temp_text, temp_color)
            
            # Draw precipitation if > 0
            precip = block_data["total_precip"]
            if precip > 0:
                precip_text = f"{int(precip)}mm"
                self._draw_text_3x5(draw, wide_canvas, x_pos + 9, 5, precip_text[:3], RAIN_BLUE)
            
            x_pos += block_width
        
        # Create scroll frames
        scroll_positions = []
        if canvas_width > DISPLAY_WIDTH:
            for offset in range(0, canvas_width - DISPLAY_WIDTH + 1, 2):
                scroll_positions.append(offset)
            for _ in range(10):
                scroll_positions.append(canvas_width - DISPLAY_WIDTH)
        else:
            scroll_positions = [0]
        
        for offset in scroll_positions:
            frame = wide_canvas.crop((offset, 0, offset + DISPLAY_WIDTH, DISPLAY_HEIGHT))
            frames.append(frame)
        
        return frames

    async def generate_week_gif(self, coordinator, entry) -> bytes:
        """Generate the 'Week' GIF showing days +2 to +9."""
        cache_key = f"{entry.entry_id}_week"
        data_hash = self._calculate_data_hash(coordinator.data)
        
        if cache_key in self._cache and self._cache_hashes.get(cache_key) == data_hash:
            _LOGGER.debug("Returning cached Week GIF")
            return self._cache[cache_key]
        
        _LOGGER.info("Generating new Week GIF")
        
        # Parse data for days +2 to +9
        time_series = coordinator.data.get("timeSeries", [])
        now_local = dt_util.now()
        
        # Collect data by day
        daily_data = {}
        for entry_data in time_series:
            time_str = entry_data.get("time") or entry_data.get("validTime")
            if not time_str:
                continue
            
            entry_time = dt_util.parse_datetime(time_str)
            if not entry_time:
                continue
            
            entry_time_local = dt_util.as_local(entry_time)
            day_offset = (entry_time_local.date() - now_local.date()).days
            
            # Only days +2 to +9
            if 2 <= day_offset <= 9:
                date_key = entry_time_local.date()
                if date_key not in daily_data:
                    daily_data[date_key] = {
                        "day_name": entry_time_local.strftime("%a").upper()[:3],
                        "temps": [],
                        "precips": [],
                        "symbols": []
                    }
                
                params = entry_data.get("data") or entry_data.get("parameters", [])
                temp = self._get_parameter(params, "air_temperature", "t")
                precip = self._get_parameter(params, "precipitation_amount_median", "pmedian")
                symbol = self._get_parameter(params, "symbol_code", "Wsymb2")
                
                if temp is not None:
                    daily_data[date_key]["temps"].append(temp)
                if precip is not None:
                    daily_data[date_key]["precips"].append(precip)
                if symbol is not None:
                    daily_data[date_key]["symbols"].append(int(symbol))
        
        if not daily_data:
            _LOGGER.warning("No data found for upcoming week")
            return self._create_error_gif("NO DATA")
        
        # Aggregate daily data
        days = []
        for date_key in sorted(daily_data.keys()):
            day_info = daily_data[date_key]
            days.append({
                "name": day_info["day_name"],
                "min_temp": min(day_info["temps"]) if day_info["temps"] else None,
                "max_temp": max(day_info["temps"]) if day_info["temps"] else None,
                "total_precip": sum(day_info["precips"]) if day_info["precips"] else 0,
                "symbol": self._get_most_severe_symbol(day_info["symbols"]) if day_info["symbols"] else None
            })
        
        # Generate frames
        frames = self._generate_daily_scroll_frames(days)
        
        gif_bytes = self._create_scrolling_gif(frames, frame_duration=120)
        
        self._cache[cache_key] = gif_bytes
        self._cache_hashes[cache_key] = data_hash
        
        return gif_bytes

    def _generate_daily_scroll_frames(self, days):
        """Generate scrolling frames for daily data."""
        frames = []
        
        # Each day: 3-char name + icon + temp range + precip = ~32px
        day_width = 32
        total_width = len(days) * day_width
        
        canvas_width = max(total_width, DISPLAY_WIDTH)
        wide_canvas = Image.new('RGB', (canvas_width, DISPLAY_HEIGHT), BLACK)
        draw = ImageDraw.Draw(wide_canvas)
        
        x_pos = 0
        for day in days:
            # Draw day name
            self._draw_text_3x5(draw, wide_canvas, x_pos, 0, day["name"], WHITE)
            
            # Draw icon
            if day["symbol"]:
                icon_pixels = get_icon_pixels(day["symbol"])
                self._draw_icon(draw, wide_canvas, x_pos + 13, 0, icon_pixels)
            
            # Draw temperature range
            if day["min_temp"] is not None and day["max_temp"] is not None:
                temp_text = f"{int(day['min_temp'])}-{int(day['max_temp'])}"
                temp_color = self._get_temp_color(day["max_temp"])
                self._draw_text_3x5(draw, wide_canvas, x_pos + 22, 0, temp_text[:5], temp_color)
            
            # Draw precipitation if > 0
            if day["total_precip"] > 0:
                precip_text = f"{int(day['total_precip'])}mm"
                self._draw_text_3x5(draw, wide_canvas, x_pos + 22, 5, precip_text[:4], RAIN_BLUE)
            
            x_pos += day_width
        
        # Create scroll frames
        scroll_positions = []
        if canvas_width > DISPLAY_WIDTH:
            for offset in range(0, canvas_width - DISPLAY_WIDTH + 1, 2):
                scroll_positions.append(offset)
            for _ in range(10):
                scroll_positions.append(canvas_width - DISPLAY_WIDTH)
        else:
            scroll_positions = [0]
        
        for offset in scroll_positions:
            frame = wide_canvas.crop((offset, 0, offset + DISPLAY_WIDTH, DISPLAY_HEIGHT))
            frames.append(frame)
        
        return frames
