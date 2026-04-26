#!/usr/bin/env python3
"""Test the drawing functions locally."""

import io
from PIL import Image, ImageDraw

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 50, 50)
BLUE = (50, 150, 255)

# Test icon
TEST_ICON = [
    [RED, RED, 0, 0, 0, 0, RED, RED],
    [RED, RED, RED, 0, 0, RED, RED, RED],
    [0, RED, RED, RED, RED, RED, RED, 0],
    [0, 0, RED, RED, RED, RED, 0, 0],
    [0, 0, RED, RED, RED, RED, 0, 0],
    [0, RED, RED, RED, RED, RED, RED, 0],
    [RED, RED, RED, 0, 0, RED, RED, RED],
    [RED, RED, 0, 0, 0, 0, RED, RED],
]


def draw_icon(image, x, y, icon_pixels):
    """Draw an 8x8 icon."""
    for row_idx, row in enumerate(icon_pixels):
        for col_idx, pixel in enumerate(row):
            if pixel != 0:
                px = x + col_idx
                py = y + row_idx
                if 0 <= px < image.width and 0 <= py < image.height:
                    image.putpixel((px, py), pixel)


def draw_text_3x5(image, x, y, text, color):
    """Draw text using 3x5 font."""
    font_map = {
        "T": [[1, 1, 1], [0, 1, 0], [0, 1, 0], [0, 1, 0], [0, 1, 0]],
        "E": [[1, 1, 1], [1, 0, 0], [1, 1, 0], [1, 0, 0], [1, 1, 1]],
        "S": [[1, 1, 1], [1, 0, 0], [1, 1, 1], [0, 0, 1], [1, 1, 1]],
        "1": [[0, 1, 0], [1, 1, 0], [0, 1, 0], [0, 1, 0], [1, 1, 1]],
        "5": [[1, 1, 1], [1, 0, 0], [1, 1, 1], [0, 0, 1], [1, 1, 1]],
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
            current_x += 4


# Create test image
img = Image.new("RGB", (32, 8), BLACK)

# Draw test text
draw_text_3x5(img, 1, 0, "TEST", WHITE)

# Draw test icon
draw_icon(img, 20, 0, TEST_ICON)

# Draw temperature
draw_text_3x5(img, 1, 6, "15", BLUE)

# Save
img.save("test_drawing.gif", format="GIF")
print("✅ Created test_drawing.gif")
print("   - Should show: 'TEST' in white at top left")
print("   - Red icon in top right")
print("   - '15' in blue at bottom left")
