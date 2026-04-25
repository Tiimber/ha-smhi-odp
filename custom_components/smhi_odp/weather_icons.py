"""Weather icons for Ulanzi display (8x8 pixels)."""

# Icon format: 8x8 grid where each value is (R, G, B) tuple
# 0 = transparent/black, or specific RGB values

# Colors
CLEAR = (255, 255, 100)  # Yellow
CLOUD_LIGHT = (200, 200, 200)  # Light gray
CLOUD_DARK = (120, 120, 120)  # Dark gray
RAIN = (0, 100, 255)  # Blue
THUNDER = (255, 255, 0)  # Bright yellow
SNOW = (240, 240, 255)  # White-blue
WIND = (255, 200, 0)  # Orange
BLACK = (0, 0, 0)

# Simple pixel art icons (8x8)
# Each icon is a list of 8 rows, each row has 8 pixels

ICONS = {
    # Clear sky - sun
    "clear": [
        [0, 0, CLEAR, 0, 0, CLEAR, 0, 0],
        [0, 0, 0, CLEAR, CLEAR, 0, 0, 0],
        [CLEAR, 0, CLEAR, CLEAR, CLEAR, CLEAR, 0, CLEAR],
        [0, CLEAR, CLEAR, CLEAR, CLEAR, CLEAR, CLEAR, 0],
        [0, CLEAR, CLEAR, CLEAR, CLEAR, CLEAR, CLEAR, 0],
        [CLEAR, 0, CLEAR, CLEAR, CLEAR, CLEAR, 0, CLEAR],
        [0, 0, 0, CLEAR, CLEAR, 0, 0, 0],
        [0, 0, CLEAR, 0, 0, CLEAR, 0, 0],
    ],
    
    # Partly cloudy
    "partly_cloudy": [
        [0, CLEAR, 0, 0, 0, 0, 0, 0],
        [CLEAR, 0, CLEAR, 0, CLOUD_LIGHT, CLOUD_LIGHT, 0, 0],
        [0, CLEAR, 0, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, 0],
        [0, 0, CLOUD_DARK, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_DARK],
        [0, CLOUD_DARK, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_DARK, 0],
        [CLOUD_DARK, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_DARK, 0, 0],
        [CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
    
    # Cloudy
    "cloudy": [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, 0, 0, 0],
        [0, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, 0, 0],
        [CLOUD_DARK, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_DARK, 0],
        [CLOUD_DARK, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_DARK, 0],
        [CLOUD_DARK, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_DARK, 0, 0],
        [0, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
    
    # Fog
    "fog": [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
    
    # Rain
    "rain": [
        [0, 0, CLOUD_LIGHT, CLOUD_LIGHT, 0, 0, 0, 0],
        [CLOUD_DARK, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_DARK, 0, 0],
        [CLOUD_DARK, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_DARK, 0, 0],
        [0, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, 0, 0, 0],
        [0, RAIN, 0, RAIN, 0, RAIN, 0, 0],
        [RAIN, 0, RAIN, 0, RAIN, 0, 0, 0],
        [0, RAIN, 0, RAIN, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
    
    # Heavy rain
    "heavy_rain": [
        [0, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, 0, 0, 0],
        [CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, 0, 0],
        [CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, 0, 0],
        [0, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, 0, 0, 0],
        [RAIN, 0, RAIN, 0, RAIN, 0, RAIN, 0],
        [0, RAIN, 0, RAIN, 0, RAIN, 0, RAIN],
        [RAIN, 0, RAIN, 0, RAIN, 0, RAIN, 0],
        [0, RAIN, 0, RAIN, 0, RAIN, 0, 0],
    ],
    
    # Thunder
    "thunder": [
        [0, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, 0, 0, 0, 0],
        [CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, 0, 0, 0],
        [CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, 0, 0, 0],
        [0, 0, THUNDER, THUNDER, 0, 0, 0, 0],
        [0, 0, 0, THUNDER, THUNDER, 0, 0, 0],
        [0, 0, THUNDER, THUNDER, 0, 0, 0, 0],
        [0, THUNDER, THUNDER, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
    
    # Snow
    "snow": [
        [0, 0, CLOUD_LIGHT, CLOUD_LIGHT, 0, 0, 0, 0],
        [CLOUD_DARK, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_DARK, 0, 0],
        [CLOUD_DARK, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_DARK, 0, 0],
        [0, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, 0, 0, 0],
        [0, SNOW, 0, SNOW, 0, SNOW, 0, 0],
        [SNOW, 0, SNOW, 0, SNOW, 0, 0, 0],
        [0, SNOW, 0, SNOW, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
    
    # Sleet
    "sleet": [
        [0, 0, CLOUD_LIGHT, CLOUD_LIGHT, 0, 0, 0, 0],
        [CLOUD_DARK, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_DARK, 0, 0],
        [CLOUD_DARK, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_LIGHT, CLOUD_DARK, 0, 0],
        [0, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, CLOUD_DARK, 0, 0, 0],
        [0, RAIN, 0, SNOW, 0, RAIN, 0, 0],
        [SNOW, 0, RAIN, 0, SNOW, 0, 0, 0],
        [0, RAIN, 0, SNOW, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
    
    # Wind
    "wind": [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [WIND, WIND, WIND, WIND, WIND, 0, 0, 0],
        [0, 0, 0, 0, WIND, 0, 0, 0],
        [0, 0, 0, WIND, 0, 0, 0, 0],
        [0, WIND, WIND, WIND, WIND, WIND, WIND, 0],
        [WIND, 0, 0, 0, 0, 0, 0, 0],
        [WIND, WIND, WIND, WIND, WIND, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
}


def get_icon_for_symbol(symbol_code):
    """Map SMHI Wsymb2 code to icon name."""
    # SMHI symbol codes
    if symbol_code in [1]:  # Clear
        return "clear"
    elif symbol_code in [2, 3, 4]:  # Partly cloudy
        return "partly_cloudy"
    elif symbol_code in [5, 6]:  # Cloudy
        return "cloudy"
    elif symbol_code in [7]:  # Fog
        return "fog"
    elif symbol_code in [8, 9, 18, 19]:  # Light/moderate rain
        return "rain"
    elif symbol_code in [10, 20]:  # Heavy rain
        return "heavy_rain"
    elif symbol_code in [11, 21]:  # Thunder
        return "thunder"
    elif symbol_code in [12, 13, 14, 22, 23, 24]:  # Sleet
        return "sleet"
    elif symbol_code in [15, 16, 17, 25, 26, 27]:  # Snow
        return "snow"
    else:
        return "cloudy"  # Default


def get_icon_pixels(symbol_code):
    """Get the 8x8 pixel array for a weather symbol."""
    icon_name = get_icon_for_symbol(symbol_code)
    return ICONS.get(icon_name, ICONS["cloudy"])
