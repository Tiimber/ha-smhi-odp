"""The SMHI ODP integration."""
import logging
from datetime import timedelta
import httpx

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import httpx_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    Platform,
)

# This import must match your folder name and const.py
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Define the platform you want to load (sensor)
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.WEATHER]


class SmhiDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the SMHI ODP API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the coordinator."""
        # --- DEBUG LOG REMOVED ---
        
        self.latitude = entry.data.get(CONF_LATITUDE)
        self.longitude = entry.data.get(CONF_LONGITUDE)
        self.client = httpx_client.get_async_client(hass)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=60),
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        # --- DEBUG LOG REMOVED ---
        
        # Format coordinates to 6 decimal places
        lat_str = f"{self.latitude:.6f}"
        lon_str = f"{self.longitude:.6f}"
        
        # *** FIX: Reverted to your 'snow1g' API URL ***
        api_url = f"https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/{lon_str}/lat/{lat_str}/data.json"
        
        try:
            # --- DEBUG LOG REMOVED ---
            response = await self.client.get(api_url)
            response.raise_for_status()  # Raises error for 4xx or 5xx status
            
            # --- DEBUG LOG REMOVED ---
            return response.json()
        
        except httpx.HTTPStatusError as err:
            _LOGGER.error(f"SMHI ODP API error: {err}")
            raise UpdateFailed(f"Error fetching data from SMHI: {err}") from err
        except httpx.RequestError as err:
            _LOGGER.error(f"SMHI ODP connection error: {err}")
            raise UpdateFailed(f"Connection error fetching data from SMHI: {err}") from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMHI ODP from a config entry."""
    
    #_LOGGER.warning("SMHI_ODP: Setting up config entry.")

    # Create the coordinator
    coordinator = SmhiDataUpdateCoordinator(hass, entry)

    # Fetch initial data so we have it when platforms are set up
    #_LOGGER.warning("SMHI_ODP: Performing first data refresh...")
    await coordinator.async_config_entry_first_refresh()
    #_LOGGER.warning("SMHI_ODP: First data refresh complete.")

    # Store the coordinator in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    #_LOGGER.warning("SMHI_ODP: Unloading config entry.")
    
    # Unload the sensor platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    # Remove the coordinator from hass.data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
