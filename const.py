"""Constants for the SMHI ODP integration."""
from datetime import timedelta

DOMAIN = "smhi_odp"

# Set the update interval to 1 hour
SCAN_INTERVAL = timedelta(hours=1)

# This is the new line that was missing
ATTRIBUTION = "Weather data from SMHI Open Data (https://opendata.smhi.se/)"
