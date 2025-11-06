# SMHI ODP Weather Component

This is a custom component for Home Assistant to integrate weather forecast data from the SMHI (Sveriges meteorologiska och hydrologiska institut) Open Data (ODP) API.

## Features

This component provides two main sets of sensors:

### 1. Current Conditions
* **Temperature:** Current air temperature.
* **Humidity:** Current relative humidity.
* **Wind Speed:** Current wind speed.
* **Wind Direction:** Current wind direction.
* **Pressure:** Current air pressure.
* **Precipitation:** Current mean precipitation amount.

### 2. Daily Forecasts
Ten sensors representing the forecast for the next 10 days:
* `sensor.smhi_odp_home_today`
* `sensor.smhi_odp_home_tomorrow`
* `sensor.smhi_odp_home_day_2`
* `sensor.smhi_odp_home_day_3`
* `sensor.smhi_odp_home_day_4`
* `sensor.smhi_odp_home_day_5`
* `sensor.smhi_odp_home_day_6`
* `sensor.smhi_odp_home_day_7`
* `sensor.smhi_odp_home_day_8`
* `sensor.smhi_odp_home_day_9`

The main state of each daily sensor is the **maximum temperature** for that day. All other forecast parameters for that time (humidity, wind, precipitation, etc.) are available as attributes.

## Installation

### Manual Installation
1.  Copy the `smhi_odp` folder (containing `__init__.py`, `sensor.py`, `const.py`, etc.) into your Home Assistant's `custom_components` directory.
2.  Restart Home Assistant.

### HACS (Home Assistant Community Store)
This component is not yet in the default HACS store. You can add it as a custom repository:
1.  Go to HACS > Integrations > (three dots in top right) > Custom repositories.
2.  Paste the URL to this GitHub repository.
3.  Select "Integration" as the category.
4.  Click "Add", then find the component in HACS and install it.

## Configuration

This component is configured via the Home Assistant UI.

1.  Go to **Settings > Devices & Services**.
2.  Click **"Add Integration"** and search for **"SMHI ODP"**.
3.  Follow the prompts to enter:
    * **Name:** A friendly name for this instance (e.g., "Home").
    * **Latitude:** Your latitude.
    * **Longitude:** Your longitude.
4.  The component will be set up and your sensors will be created.

**Please note** that the component might take a little while to process the initial data from the API.