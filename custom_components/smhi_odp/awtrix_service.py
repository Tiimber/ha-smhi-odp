"""AWTRIX display service for weather animations using draw commands."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

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


class AwtrixWeatherService:
    """Service to generate AWTRIX weather animations."""

    def __init__(self):
        """Initialize the AWTRIX service."""
        pass

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
