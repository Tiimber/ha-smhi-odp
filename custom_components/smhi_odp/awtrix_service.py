"""AWTRIX display service for weather animations using draw commands."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any
from pathlib import Path

from PIL import Image

from homeassistant.util import dt as dt_util

from .weather_icons import ICONS

_LOGGER = logging.getLogger(__name__)


def rgb_to_hex(rgb):
    """Convert RGB tuple to hex color string."""
    if rgb == 0:
        return "#000000"
    if isinstance(rgb, tuple):
        return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
    return "#000000"


def icon_to_draw_commands(icon_pixels, offset_x=0, offset_y=0):
    """
    Convert 8x8 icon pixel array to AWTRIX draw commands.
    
    Groups contiguous same-color pixels into rectangles for efficiency.
    """
    if not icon_pixels:
        return []
    
    draw_commands = []
    
    # Simple approach: draw each pixel individually
    # TODO: optimize by grouping contiguous pixels into rectangles
    for y, row in enumerate(icon_pixels):
        for x, pixel in enumerate(row):
            if pixel != 0:  # Skip transparent pixels
                color = rgb_to_hex(pixel)
                draw_commands.append({
                    "dp": [offset_x + x, offset_y + y, color]
                })
    
    return draw_commands


def get_weather_icon_name(symbol_code):
    """Map SMHI symbol code to our icon name."""
    # SMHI symbol codes: 1-27
    # 1: Clear sky
    # 2: Nearly clear sky  
    # 3-4: Variable cloudiness
    # 5-6: Cloudy/Overcast
    # 7: Fog
    # 8-14: Rain (light to heavy)
    # 15-20: Snow (light to heavy)
    # 21: Thunder
    # 22-27: Sleet variations
    
    symbol_map = {
        1: "clear",
        2: "partly_cloudy",
        3: "partly_cloudy",
        4: "partly_cloudy",
        5: "cloudy",
        6: "cloudy",
        7: "fog",
        8: "rain_light",
        9: "rain_light",
        10: "rain",
        11: "rain",
        12: "rain_heavy",
        13: "rain_heavy",
        14: "rain_heavy",
        15: "snow_light",
        16: "snow_light",
        17: "snow",
        18: "snow",
        19: "snow_heavy",
        20: "snow_heavy",
        21: "thunder",
        22: "rain",  # Sleet
        23: "rain",
        24: "rain",
        25: "rain",
        26: "rain",
        27: "rain",
    }
    
    return symbol_map.get(symbol_code, "cloudy")


def get_temp_color(temp):
    """Get hex color for temperature value."""
    if temp < 0:
        return "#64A0FF"  # Blue cold
    elif temp < 10:
        return "#3296FF"  # Blue
    elif temp < 20:
        return "#32FF64"  # Green
    elif temp < 30:
        return "#FF9600"  # Orange
    else:
        return "#FF3232"  # Red


def parse_gif_to_frames(gif_path: str, frame_duration: int = None) -> list[dict]:
    """
    Parse a GIF file and convert each frame to AWTRIX draw commands.
    
    Args:
        gif_path: Path to the GIF file
        frame_duration: Optional override for frame duration in milliseconds (uses GIF's duration if not set)
    
    Returns:
        List of AWTRIX payload dicts with draw commands and frame_delay_ms for automation timing
    """
    try:
        img = Image.open(gif_path)
        frames = []
        
        # Get number of frames
        n_frames = getattr(img, "n_frames", 1)
        _LOGGER.info(f"Parsing GIF {gif_path}: {n_frames} frames")
        
        for frame_num in range(n_frames):
            img.seek(frame_num)
            
            # Get frame duration from GIF (in milliseconds), default to 100ms if not specified
            gif_duration_ms = img.info.get('duration', 100)
            
            # Use override if provided, otherwise use GIF's duration
            duration_ms = frame_duration if frame_duration is not None else gif_duration_ms
            duration_seconds = duration_ms / 1000.0
            
            # Convert to RGB mode if needed
            if img.mode != 'RGB':
                frame_img = img.convert('RGB')
            else:
                frame_img = img.copy()
            
            # Get frame dimensions
            width, height = frame_img.size
            
            # Extract pixels and create draw commands
            draw_commands = []
            pixels = frame_img.load()
            
            for y in range(height):
                for x in range(width):
                    pixel = pixels[x, y]
                    # Skip black pixels (assumed background)
                    if pixel != (0, 0, 0):
                        color = f"#{pixel[0]:02X}{pixel[1]:02X}{pixel[2]:02X}"
                        draw_commands.append({
                            "dp": [x, y, color]
                        })
            
            # Create AWTRIX payload for this frame
            payload = {
                "draw": draw_commands,
                "frame_delay_ms": duration_ms  # For automation to know how long to wait
            }
            
            frames.append(payload)
            _LOGGER.debug(f"Frame {frame_num + 1}: {len(draw_commands)} pixels, {duration_seconds:.3f}s delay")
        
        _LOGGER.info(f"Parsed {len(frames)} frames from {gif_path}")
        return frames
        
    except Exception as e:
        _LOGGER.error(f"Error parsing GIF {gif_path}: {e}")
        return []


def image_to_draw_commands(image):
    """
    Convert a PIL Image (32x8) to AWTRIX draw commands.
    
    Args:
        image: PIL Image object (RGB mode, 32x8 pixels)
    
    Returns:
        List of draw command dicts
    """
    draw_commands = []
    pixels = image.load()
    width, height = image.size
    
    for y in range(height):
        for x in range(width):
            pixel = pixels[x, y]
            # Skip black pixels (assumed background)
            if pixel != (0, 0, 0):
                color = f"#{pixel[0]:02X}{pixel[1]:02X}{pixel[2]:02X}"
                draw_commands.append({
                    "dp": [x, y, color]
                })
    
    return draw_commands


class AwtrixWeatherService:
    """Service to generate AWTRIX weather animations."""

    def __init__(self):
        """Initialize the AWTRIX service."""
        from .display_service import WeatherDisplayService
        self.display_service = WeatherDisplayService()

    def generate_today_screens(self, forecast_data: dict[str, Any]) -> list[dict]:
        """
        Generate multiple static screens for today's hourly forecast.
        
        Splits the 24-hour forecast into 4 screens of 6 hours each.
        Each screen shows icons and temps for those hours.
        Last screen is completely black for visual separation.
        
        Returns:
            List of screen dicts with draw commands and duration
        """
        time_series = forecast_data.get("timeSeries", [])
        
        if not time_series:
            _LOGGER.warning("No time series data available")
            return []
        
        screens = []
        hours_per_screen = 6
        
        # Generate 4 screens (0-5h, 6-11h, 12-17h, 18-23h)
        for screen_num in range(4):
            start_hour = screen_num * hours_per_screen
            end_hour = start_hour + hours_per_screen
            
            # Create a 32x8 image for this screen
            img = Image.new('RGB', (32, 8), (0, 0, 0))
            
            # Draw hours for this screen (each hour gets ~5 pixels width)
            x_offset = 0
            for hour_idx in range(start_hour, min(end_hour, len(time_series))):
                hour_data = time_series[hour_idx]
                parameters = hour_data.get("parameters", {})
                
                # Get temperature and symbol
                temp = parameters.get("air_temperature")
                symbol = parameters.get("symbol_code")
                
                if temp is not None and symbol is not None:
                    # Draw weather icon (8x8) at top, but we only have 8px height
                    # So we'll do: 3px for hour number, 5px for icon/temp
                    icon_name = get_weather_icon_name(symbol)
                    icon_pixels = ICONS.get(icon_name, ICONS["cloudy"])
                    
                    # Scale down icon to fit (use top 5 pixels of the 8x8 icon)
                    for y in range(5):
                        for x in range(5):
                            if y < len(icon_pixels) and x < len(icon_pixels[y]):
                                pixel = icon_pixels[y][x]
                                if pixel != 0:
                                    img.putpixel((x_offset + x, y), pixel)
                    
                    # Draw temperature below (last 3 pixels)
                    temp_color = get_temp_color(temp)
                    temp_str = f"{int(temp)}"
                    # Simple pixel representation of the number
                    self.display_service._draw_text_3x5(
                        None, img, x_offset, 5, temp_str, temp_color
                    )
                
                x_offset += 5  # 5 pixels per hour + 1 spacing
            
            # Convert image to draw commands
            draw_commands = image_to_draw_commands(img)
            
            screens.append({
                "draw": draw_commands,
                "duration": 3  # Show each screen for 3 seconds
            })
            
            _LOGGER.debug(f"Today screen {screen_num + 1}: {len(draw_commands)} pixels")
        
        # Add black screen at the end
        screens.append({
            "draw": [],  # Empty = black screen
            "duration": 1
        })
        
        return screens

    def generate_tomorrow_screens(self, forecast_data: dict[str, Any]) -> list[dict]:
        """
        Generate static screens for tomorrow's forecast.
        
        Splits the 4 blocks into 2 screens (night+morning, afternoon+evening).
        Last screen is completely black.
        
        Returns:
            List of screen dicts
        """
        time_series = forecast_data.get("timeSeries", [])
        
        if not time_series:
            return []
        
        # Aggregate into 4 blocks (as in original GIF generation)
        blocks = []
        for i in range(4):
            start_idx = i * 6 + 24  # Skip first 24 hours (today)
            end_idx = start_idx + 6
            
            if start_idx < len(time_series):
                block_hours = time_series[start_idx:min(end_idx, len(time_series))]
                # Average temperature, most common symbol, sum precipitation
                if block_hours:
                    temps = []
                    symbols = []
                    precip = []
                    
                    for hour in block_hours:
                        params = hour.get("parameters", {})
                        if params.get("air_temperature") is not None:
                            temps.append(params["air_temperature"])
                        if params.get("symbol_code") is not None:
                            symbols.append(params["symbol_code"])
                        if params.get("precipitation_amount_median") is not None:
                            precip.append(params["precipitation_amount_median"])
                    
                    if temps and symbols:
                        blocks.append({
                            "temp": sum(temps) / len(temps),
                            "symbol": max(set(symbols), key=symbols.count),
                            "precip": sum(precip) if precip else 0
                        })
        
        screens = []
        
        # Screen 1: Night + Morning
        img = Image.new('RGB', (32, 8), (0, 0, 0))
        for block_idx in range(min(2, len(blocks))):
            block = blocks[block_idx]
            icon_name = get_weather_icon_name(block["symbol"])
            icon_pixels = ICONS.get(icon_name, ICONS["cloudy"])
            
            x_offset = block_idx * 16  # 16 pixels per block
            
            # Draw icon
            self.display_service._draw_icon(None, img, x_offset, 0, icon_pixels)
            
            # Draw temp
            temp_color = get_temp_color(block["temp"])
            temp_str = f"{int(block['temp'])}"
            self.display_service._draw_text_3x5(
                None, img, x_offset + 9, 2, temp_str, temp_color
            )
        
        screens.append({
            "draw": image_to_draw_commands(img),
            "duration": 3
        })
        
        # Screen 2: Afternoon + Evening
        if len(blocks) > 2:
            img = Image.new('RGB', (32, 8), (0, 0, 0))
            for block_idx in range(2, min(4, len(blocks))):
                block = blocks[block_idx]
                icon_name = get_weather_icon_name(block["symbol"])
                icon_pixels = ICONS.get(icon_name, ICONS["cloudy"])
                
                x_offset = (block_idx - 2) * 16
                
                # Draw icon
                self.display_service._draw_icon(None, img, x_offset, 0, icon_pixels)
                
                # Draw temp
                temp_color = get_temp_color(block["temp"])
                temp_str = f"{int(block['temp'])}"
                self.display_service._draw_text_3x5(
                    None, img, x_offset + 9, 2, temp_str, temp_color
                )
            
            screens.append({
                "draw": image_to_draw_commands(img),
                "duration": 3
            })
        
        # Black screen
        screens.append({
            "draw": [],
            "duration": 1
        })
        
        return screens

    def generate_week_screens(self, forecast_data: dict[str, Any]) -> list[dict]:
        """
        Generate static screens for 8-day forecast.
        
        Splits into 4 screens of 2 days each.
        Last screen is completely black.
        
        Returns:
            List of screen dicts
        """
        time_series = forecast_data.get("timeSeries", [])
        
        if not time_series:
            return []
        
        # Aggregate into daily forecasts
        daily_forecasts = []
        for day_offset in range(8):
            start_idx = day_offset * 24
            end_idx = start_idx + 24
            
            if start_idx < len(time_series):
                day_hours = time_series[start_idx:min(end_idx, len(time_series))]
                
                if day_hours:
                    temps = []
                    symbols = []
                    
                    for hour in day_hours:
                        params = hour.get("parameters", {})
                        if params.get("air_temperature") is not None:
                            temps.append(params["air_temperature"])
                        if params.get("symbol_code") is not None:
                            symbols.append(params["symbol_code"])
                    
                    if temps and symbols:
                        daily_forecasts.append({
                            "temp": sum(temps) / len(temps),
                            "symbol": max(set(symbols), key=symbols.count)
                        })
        
        screens = []
        
        # Generate 4 screens (2 days each)
        for screen_num in range(4):
            img = Image.new('RGB', (32, 8), (0, 0, 0))
            
            for day_idx in range(2):
                forecast_idx = screen_num * 2 + day_idx
                
                if forecast_idx < len(daily_forecasts):
                    forecast = daily_forecasts[forecast_idx]
                    icon_name = get_weather_icon_name(forecast["symbol"])
                    icon_pixels = ICONS.get(icon_name, ICONS["cloudy"])
                    
                    x_offset = day_idx * 16  # 16 pixels per day
                    
                    # Draw icon
                    self.display_service._draw_icon(None, img, x_offset, 0, icon_pixels)
                    
                    # Draw temp
                    temp_color = get_temp_color(forecast["temp"])
                    temp_str = f"{int(forecast['temp'])}"
                    self.display_service._draw_text_3x5(
                        None, img, x_offset + 9, 2, temp_str, temp_color
                    )
            
            screens.append({
                "draw": image_to_draw_commands(img),
                "duration": 3
            })
        
        # Black screen
        screens.append({
            "draw": [],
            "duration": 1
        })
        
        return screens

    def generate_current_weather(
        self, forecast_data: dict[str, Any]
    ) -> dict:
        """
        Generate a single comprehensive AWTRIX screen for current weather.
        
        Shows: Current weather icon + temp, next 2 hours as text
        """
        time_series = forecast_data.get("timeSeries", [])
        
        if not time_series:
            _LOGGER.warning("No time series data available")
            return {}
        
        # Get current hour (first entry)
        current = time_series[0]
        parameters = current.get("data") or current.get("parameters", {})
        
        temp = self._get_parameter(parameters, "air_temperature", "t")
        symbol = self._get_parameter(parameters, "symbol_code", "Wsymb2")
        precip = self._get_parameter(parameters, "precipitation_amount_median", "pmedian")
        
        if temp is None:
            _LOGGER.warning("No temperature data")
            return {}
        
        # Current temperature
        temp_int = round(temp)
        temp_color = get_temp_color(temp)
        
        # Get weather icon
        icon_name = get_weather_icon_name(symbol or 2)
        icon_pixels = ICONS.get(icon_name, ICONS.get("cloudy"))
        draw_commands = icon_to_draw_commands(icon_pixels, offset_x=0, offset_y=0)
        
        # Build text with current + next hours
        text_parts = [f" {temp_int}°"]
        
        # Add next 2-3 hours
        for i in range(1, min(4, len(time_series))):
            entry = time_series[i]
            params = entry.get("data") or entry.get("parameters", {})
            next_temp = self._get_parameter(params, "air_temperature", "t")
            if next_temp:
                text_parts.append(f"{round(next_temp)}°")
        
        text = " ".join(text_parts)
        
        # Add precipitation if significant
        if precip and precip > 0.5:
            text += f" {precip:.1f}mm"
        
        payload = {
            "text": text,
            "textColor": temp_color,
            "draw": draw_commands,
            "rainbow": False,
            "scrollSpeed": 50,
            "lifetime": 900  # 15 minutes
        }
        
        _LOGGER.info(f"Generated current weather display: {text}")
        return payload

    def _get_parameter(self, parameters, param_name, fallback_name=None):
        """
        Extract parameter value from SMHI data.
        
        Handles both object format (snow1g):
          {"air_temperature": 2.9, "symbol_code": 1}
        And array format (metfcst):
          [{"name": "t", "values": [10.5]}]
        """
        if isinstance(parameters, dict):
            # Object format (snow1g)
            value = parameters.get(param_name)
            if value is None and fallback_name:
                value = parameters.get(fallback_name)
            return value
        elif isinstance(parameters, list):
            # Array format (metfcst)
            for param in parameters:
                if param.get("name") == param_name:
                    values = param.get("values", [])
                    return values[0] if values else None
                if fallback_name and param.get("name") == fallback_name:
                    values = param.get("values", [])
                    return values[0] if values else None
        return None

    def generate_today_animation(
        self, forecast_data: dict[str, Any], hours: int = 6
    ) -> list[dict]:
        """
        Generate AWTRIX animation frames for today's hourly forecast.
        
        Returns a list of MQTT payloads, one per hour.
        """
        time_series = forecast_data.get("timeSeries", [])
        
        if not time_series:
            _LOGGER.warning("No time series data available for today animation")
            return []
        
        frames = []
        
        # Get the next N hours
        for i in range(min(hours, len(time_series))):
            entry = time_series[i]
            valid_time = entry.get("validTime", "")
            
            # Parse time
            try:
                dt = datetime.fromisoformat(valid_time.replace("Z", "+00:00"))
                hour_str = dt.strftime("%H")
            except Exception as e:
                _LOGGER.warning(f"Failed to parse time {valid_time}: {e}")
                hour_str = f"{i:02d}"
            
            # Get weather data
            parameters = entry.get("data") or entry.get("parameters", {})
            
            temp = self._get_parameter(parameters, "air_temperature", "t")
            symbol = self._get_parameter(parameters, "symbol_code", "Wsymb2")
            precip = self._get_parameter(parameters, "precipitation_amount_median", "pmedian")
            
            if temp is None:
                _LOGGER.warning(f"No temperature data for hour {i}")
                continue
            
            # Round temperature
            temp_int = round(temp)
            temp_str = f"{temp_int}°"
            
            # Get weather icon
            icon_name = get_weather_icon_name(symbol or 2)
            icon_pixels = ICONS.get(icon_name, ICONS.get("cloudy"))
            
            # Create draw commands
            draw_commands = icon_to_draw_commands(icon_pixels, offset_x=0, offset_y=0)
            
            # Temperature text
            temp_color = get_temp_color(temp)
            
            # Create AWTRIX payload
            payload = {
                "text": f" {temp_str}",  # Space for icon
                "textColor": temp_color,
                "draw": draw_commands,
                "duration": 5,  # Show each hour for 5 seconds
                "lifetime": 600  # 10 minutes total lifetime
            }
            
            # Add precipitation if significant
            if precip and precip > 0.1:
                precip_str = f"{precip:.1f}mm"
                payload["text"] = f" {temp_str} {precip_str}"
            
            frames.append(payload)
            
            _LOGGER.debug(
                f"Hour {hour_str}: {temp_int}°C, symbol {symbol}, "
                f"{len(draw_commands)} draw commands"
            )
        
        _LOGGER.info(f"Generated {len(frames)} animation frames for today")
        return frames

    def generate_tomorrow_animation(
        self, forecast_data: dict[str, Any]
    ) -> list[dict]:
        """
        Generate AWTRIX animation frames for tomorrow's forecast.
        
        Shows 4 blocks: Morning, Day, Evening, Night
        """
        time_series = forecast_data.get("timeSeries", [])
        
        if not time_series:
            _LOGGER.warning("No time series data available for tomorrow animation")
            return []
        
        # Get tomorrow's data (skip first 24 hours to get tomorrow)
        now = dt_util.now()
        tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_end = tomorrow_start + timedelta(days=1)
        
        # Filter for tomorrow's entries
        tomorrow_entries = []
        for entry in time_series:
            valid_time = entry.get("validTime", "")
            try:
                dt = datetime.fromisoformat(valid_time.replace("Z", "+00:00"))
                if tomorrow_start <= dt < tomorrow_end:
                    tomorrow_entries.append(entry)
            except Exception:
                continue
        
        if not tomorrow_entries:
            _LOGGER.warning("No data for tomorrow")
            return []
        
        # Aggregate into 4 blocks
        blocks = {
            "Morning": {"hours": list(range(6, 12)), "entries": []},
            "Day": {"hours": list(range(12, 18)), "entries": []},
            "Evening": {"hours": list(range(18, 22)), "entries": []},
            "Night": {"hours": list(range(22, 24)) + list(range(0, 6)), "entries": []},
        }
        
        # Assign entries to blocks
        for entry in tomorrow_entries:
            valid_time = entry.get("validTime", "")
            try:
                dt = datetime.fromisoformat(valid_time.replace("Z", "+00:00"))
                hour = dt.hour
                for block_name, block_data in blocks.items():
                    if hour in block_data["hours"]:
                        block_data["entries"].append(entry)
                        break
            except Exception:
                continue
        
        # Create frames for each block
        frames = []
        for block_name, block_data in blocks.items():
            if not block_data["entries"]:
                continue
            
            # Average temperature
            temps = []
            symbols = []
            precips = []
            
            for entry in block_data["entries"]:
                parameters = entry.get("data") or entry.get("parameters", {})
                temp = self._get_parameter(parameters, "air_temperature", "t")
                symbol = self._get_parameter(parameters, "symbol_code", "Wsymb2")
                precip = self._get_parameter(parameters, "precipitation_amount_median", "pmedian")
                
                if temp is not None:
                    temps.append(temp)
                if symbol is not None:
                    symbols.append(symbol)
                if precip is not None:
                    precips.append(precip)
            
            if not temps:
                continue
            
            avg_temp = sum(temps) / len(temps)
            # Most common symbol
            most_common_symbol = max(set(symbols), key=symbols.count) if symbols else 2
            total_precip = sum(precips) if precips else 0
            
            temp_int = round(avg_temp)
            temp_str = f"{temp_int}°"
            
            # Get weather icon
            icon_name = get_weather_icon_name(most_common_symbol)
            icon_pixels = ICONS.get(icon_name, ICONS.get("cloudy"))
            
            # Create draw commands
            draw_commands = icon_to_draw_commands(icon_pixels, offset_x=0, offset_y=0)
            
            # Temperature text
            temp_color = get_temp_color(avg_temp)
            
            # Create AWTRIX payload
            payload = {
                "text": f" {temp_str}",
                "textColor": temp_color,
                "draw": draw_commands,
                "duration": 5,
                "lifetime": 600
            }
            
            if total_precip > 0.5:
                payload["text"] = f" {temp_str} {total_precip:.1f}mm"
            
            frames.append(payload)
            
            _LOGGER.debug(
                f"{block_name}: {temp_int}°C, symbol {most_common_symbol}, "
                f"precip {total_precip:.1f}mm"
            )
        
        _LOGGER.info(f"Generated {len(frames)} animation frames for tomorrow")
        return frames

    def generate_week_animation(
        self, forecast_data: dict[str, Any], days: int = 7
    ) -> list[dict]:
        """
        Generate AWTRIX animation frames for week forecast.
        
        Shows one frame per day with high/low temps.
        """
        time_series = forecast_data.get("timeSeries", [])
        
        if not time_series:
            _LOGGER.warning("No time series data available for week animation")
            return []
        
        # Group by day
        days_data = {}
        
        for entry in time_series:
            valid_time = entry.get("validTime", "")
            try:
                dt = datetime.fromisoformat(valid_time.replace("Z", "+00:00"))
                day_key = dt.strftime("%Y-%m-%d")
                
                if day_key not in days_data:
                    days_data[day_key] = {
                        "date": dt,
                        "entries": []
                    }
                
                days_data[day_key]["entries"].append(entry)
            except Exception:
                continue
        
        # Create frames for each day
        frames = []
        sorted_days = sorted(days_data.items())[:days]
        
        for day_key, day_info in sorted_days:
            entries = day_info["entries"]
            date = day_info["date"]
            
            # Get temps and symbols
            temps = []
            symbols = []
            
            for entry in entries:
                parameters = entry.get("data") or entry.get("parameters", {})
                temp = self._get_parameter(parameters, "air_temperature", "t")
                symbol = self._get_parameter(parameters, "symbol_code", "Wsymb2")
                
                if temp is not None:
                    temps.append(temp)
                if symbol is not None:
                    symbols.append(symbol)
            
            if not temps:
                continue
            
            high_temp = max(temps)
            low_temp = min(temps)
            most_common_symbol = max(set(symbols), key=symbols.count) if symbols else 2
            
            # Day label
            day_name = date.strftime("%a")[:2]  # "Mo", "Tu", etc.
            
            high_int = round(high_temp)
            low_int = round(low_temp)
            temp_str = f"{high_int}/{low_int}°"
            
            # Get weather icon
            icon_name = get_weather_icon_name(most_common_symbol)
            icon_pixels = ICONS.get(icon_name, ICONS.get("cloudy"))
            
            # Create draw commands
            draw_commands = icon_to_draw_commands(icon_pixels, offset_x=0, offset_y=0)
            
            # Temperature text with high/low
            temp_color = get_temp_color((high_temp + low_temp) / 2)
            
            # Create AWTRIX payload
            payload = {
                "text": f" {temp_str}",
                "textColor": temp_color,
                "draw": draw_commands,
                "duration": 5,
                "lifetime": 3600  # 1 hour
            }
            
            frames.append(payload)
            
            _LOGGER.debug(
                f"{day_name}: {high_int}/{low_int}°C, symbol {most_common_symbol}"
            )
        
        _LOGGER.info(f"Generated {len(frames)} animation frames for week")
        return frames
