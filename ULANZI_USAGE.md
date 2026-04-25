# Ulanzi TC001 Display Integration

This integration includes services to generate animated GIF weather displays optimized for the Ulanzi TC001 (32×8 pixel display).

## Services

### `smhi_odp.generate_today_gif`

Generates an animated GIF showing hourly weather for today (05:00-22:00).

**Features:**
- Hourly forecast with weather icons
- Temperature display with color-coding (blue=cold, green=mild, orange=warm, red=hot)
- Precipitation amounts (only shown when >0mm)
- Current hour highlighted with border
- Smooth horizontal scrolling animation
- Wind speed indicator (when ≥10 m/s and not storm)

**Returns:**
- `gif_bytes`: Hex-encoded GIF data
- `size`: Size in bytes

### `smhi_odp.generate_tomorrow_gif`

Generates an animated GIF showing tomorrow's forecast in time blocks.

**Features:**
- Three time blocks: Morning (05-12), Afternoon (12-18), Evening (18-22)
- Max temperature per block
- Total precipitation per block
- Most severe weather condition per block

### `smhi_odp.generate_week_gif`

Generates an animated GIF showing the upcoming 8-day forecast (days +2 to +9).

**Features:**
- Daily overview with min-max temperature range
- Total daily precipitation
- Most prominent weather condition
- Day names (MON, TUE, WED, etc.)

## Usage Examples

### Example 1: Basic Automation to Update Display

```yaml
automation:
  - alias: "Update Ulanzi Weather - Today"
    trigger:
      - platform: time_pattern
        minutes: "/30"  # Every 30 minutes
      - platform: state
        entity_id: sensor.smhi_home_temperature
    action:
      - service: smhi_odp.generate_today_gif
        response_variable: today_gif
      
      # Save to file (if needed by your display setup)
      - service: shell_command.save_gif
        data:
          filename: "/config/www/weather_today.gif"
          content: "{{ today_gif.gif_bytes }}"
```

### Example 2: Using with MQTT (AWTRIX Light)

If your Ulanzi runs AWTRIX Light firmware, you can send the GIF directly:

```yaml
automation:
  - alias: "Update Ulanzi Weather via MQTT"
    trigger:
      - platform: time_pattern
        minutes: "/15"
    action:
      # Generate the GIF
      - service: smhi_odp.generate_today_gif
        response_variable: today_gif
      
      # Save to www folder (AWTRIX can fetch via HTTP)
      - service: shell_command.save_today_gif
        data:
          content: "{{ today_gif.gif_bytes }}"
      
      # Tell AWTRIX to display it
      - service: mqtt.publish
        data:
          topic: "awtrix_PREFIX/custom/weather"
          payload: |
            {
              "icon": "http://YOUR_HA_IP:8123/local/weather_today.gif",
              "lifetime": 900
            }
```

### Example 3: Cycle Through All Three Views

```yaml
automation:
  - alias: "Cycle Weather Views on Ulanzi"
    trigger:
      - platform: time_pattern
        minutes: "/20"
    action:
      # Today view
      - service: smhi_odp.generate_today_gif
        response_variable: today_gif
      - service: shell_command.save_gif
        data:
          filename: "/config/www/weather_today.gif"
          content: "{{ today_gif.gif_bytes }}"
      
      # Wait 5 seconds
      - delay: "00:00:05"
      
      # Tomorrow view
      - service: smhi_odp.generate_tomorrow_gif
        response_variable: tomorrow_gif
      - service: shell_command.save_gif
        data:
          filename: "/config/www/weather_tomorrow.gif"
          content: "{{ tomorrow_gif.gif_bytes }}"
      
      # Wait 5 seconds
      - delay: "00:00:05"
      
      # Week view
      - service: smhi_odp.generate_week_gif
        response_variable: week_gif
      - service: shell_command.save_gif
        data:
          filename: "/config/www/weather_week.gif"
          content: "{{ week_gif.gif_bytes }}"
      
      # Update AWTRIX to cycle through them
      - service: mqtt.publish
        data:
          topic: "awtrix_PREFIX/custom/weather_today"
          payload: '{"icon": "http://YOUR_HA_IP:8123/local/weather_today.gif", "duration": 10}'
      - service: mqtt.publish
        data:
          topic: "awtrix_PREFIX/custom/weather_tomorrow"
          payload: '{"icon": "http://YOUR_HA_IP:8123/local/weather_tomorrow.gif", "duration": 10}'
      - service: mqtt.publish
        data:
          topic: "awtrix_PREFIX/custom/weather_week"
          payload: '{"icon": "http://YOUR_HA_IP:8123/local/weather_week.gif", "duration": 10}'
```

### Required Shell Commands

Add this to your `configuration.yaml`:

```yaml
shell_command:
  save_gif: 'echo "{{ content }}" | xxd -r -p > {{ filename }}'
  save_today_gif: 'echo "{{ content }}" | xxd -r -p > /config/www/weather_today.gif'
  save_tomorrow_gif: 'echo "{{ content }}" | xxd -r -p > /config/www/weather_tomorrow.gif'
  save_week_gif: 'echo "{{ content }}" | xxd -r -p > /config/www/weather_week.gif'
```

## Performance Notes

- **Caching:** GIFs are cached in memory and only regenerated when weather data changes
- **No Disk Writes:** GIFs are generated in RAM (SD card friendly for HA Green)
- **Small File Size:** Typical GIF size is 30-80KB
- **Frame Rate:** 120ms per frame for smooth scrolling

## Customization

The weather icons and colors are defined in `weather_icons.py` and can be customized if desired.

## Troubleshooting

**Service not appearing:**
- Restart Home Assistant after installation
- Check logs for errors: `cat home-assistant.log | grep smhi_odp`

**GIF not displaying:**
- Verify the GIF is saved correctly: `ls -lh /config/www/weather_*.gif`
- Check if the file is accessible via browser: `http://YOUR_HA_IP:8123/local/weather_today.gif`

**No data in GIF:**
- Ensure SMHI integration is working: check `sensor.smhi_home_temperature` exists
- Check coordinator data is being fetched: look for SMHI API errors in logs
