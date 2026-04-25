#!/usr/bin/env python3
"""Analyze the generated GIF to see what pixels are set."""
from PIL import Image

# Load the GIF
img = Image.open("weather_tomorrow.gif")

print(f"Image size: {img.size}")
print(f"Mode: {img.mode}")
n_frames = getattr(img, 'n_frames', 1)
print(f"Frames: {n_frames}")
print()

# Analyze each frame
for frame_num in range(min(n_frames, 5)):  # Check first 5 frames
    img.seek(frame_num)
    if img.mode == 'P':  # Palette mode
        frame_rgb = img.convert('RGB')
    else:
        frame_rgb = img
    
    print(f"Frame {frame_num}:")
    
    # Count non-black pixels by row
    by_row = {}
    for y in range(frame_rgb.height):
        for x in range(frame_rgb.width):
            pixel = frame_rgb.getpixel((x, y))
            if pixel != (0, 0, 0):  # Not black
                if y not in by_row:
                    by_row[y] = []
                by_row[y].append((x, pixel))
    
    if by_row:
        for y in sorted(by_row.keys()):
            pixels = by_row[y]
            x_range = f"{min(p[0] for p in pixels)}-{max(p[0] for p in pixels)}"
            colors = set(p[1] for p in pixels)
            print(f"  Row {y}: {len(pixels)} pixels at x={x_range}, colors={len(colors)}")
    else:
        print("  All black!")
    print()
