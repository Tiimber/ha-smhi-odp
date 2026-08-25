"""The SMHI ODP integration."""
import logging
from datetime import timedelta
import httpx
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import httpx_client, config_validation as cv, entity_registry as er
from homeassistant.helpers.sun import is_up
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    Platform,
)

# This import must match your folder name and const.py
from .const import DOMAIN
from .device_panel_service import generate_weather_screen

_LOGGER = logging.getLogger(__name__)

DEVICE_PANEL_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
    }
)

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


async def _fetch_temperature_history(hass: HomeAssistant, entry_id: str, start, end):
    """Real recorder history for the weather entity's temperature attribute.

    Used to backfill the device panel's temperature graph for the part of
    today that has already happened. SMHI's API is forecast-only - it has
    nothing for hours that already elapsed - but the recorder has been
    logging this entity's state (attributes included) all along, so no
    bespoke rolling-memory mechanism is needed.
    """
    entity_id = er.async_get(hass).async_get_entity_id("weather", DOMAIN, f"{entry_id}_weather")
    if not entity_id:
        _LOGGER.warning("No weather entity registered for entry_id %s", entry_id)
        return []

    from homeassistant.components.recorder import history, get_instance

    def _query():
        return history.state_changes_during_period(
            hass, start, end, entity_id, include_start_time_state=True
        )

    try:
        result = await get_instance(hass).async_add_executor_job(_query)
    except Exception as err:  # recorder not set up, entity purged, etc.
        _LOGGER.warning("Could not fetch history for %s: %s", entity_id, err)
        return []

    points = []
    for state in result.get(entity_id, []):
        temp = state.attributes.get("temperature")
        if temp is not None:
            points.append((dt_util.as_local(state.last_changed), temp))
    return points


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

    # Register services (only once for the domain)
    if not hass.services.has_service(DOMAIN, "generate_device_panel_screen"):

        async def handle_generate_device_panel_screen(call: ServiceCall):
            """Render the device panel weather screen and save it to /config/www/.

            Opt-in: does nothing unless the target config entry has
            "enable_device_panel_export" turned on in its options (see
            SmhiOdpOptionsFlow). Off by default, so this stays invisible
            to anyone who hasn't asked for it.
            """
            entry_id = call.data.get("entry_id", entry.entry_id)
            target_entry = hass.config_entries.async_get_entry(entry_id)
            coord = hass.data[DOMAIN].get(entry_id)

            if not target_entry or not coord:
                _LOGGER.error("No config entry/coordinator found for entry_id: %s", entry_id)
                return {"success": False, "error": "No coordinator found"}

            if not target_entry.options.get("enable_device_panel_export", False):
                _LOGGER.warning(
                    "generate_device_panel_screen called but device panel export "
                    "is not enabled in options for entry %s",
                    entry_id,
                )
                return {"success": False, "error": "enable_device_panel_export is off"}

            now = dt_util.now()
            today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            history_points = await _fetch_temperature_history(
                hass, entry_id, today_midnight, now
            )

            jpeg_bytes = await hass.async_add_executor_job(
                generate_weather_screen, coord.data, is_up(hass), history_points
            )

            filename = "smhi_odp_panel.jpg"
            filepath = hass.config.path("www", filename)

            def write_file():
                with open(filepath, "wb") as f:
                    f.write(jpeg_bytes)

            await hass.async_add_executor_job(write_file)
            _LOGGER.info("Saved %s: %d bytes", filename, len(jpeg_bytes))

            # Tell the caller when to come back. A small wall-powered panel
            # typically has no RTC or NTP - only a millisecond counter - so
            # it cannot work out "just after the top of the hour" itself.
            # Deciding it here also means the cadence can be retuned without
            # reflashing the device.
            #
            # The image is always current (it renders on demand), so this
            # isn't about waiting for a scheduled render. It's about the
            # forecast row's leading slots being "the next two hours", which
            # go stale the moment the clock rolls over. By just after the
            # hour the coordinator's own hourly poll has usually landed too.
            next_hour = (now + timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0
            )
            next_refresh_s = int((next_hour - now).total_seconds()) + 120

            return {
                "success": True,
                "filename": filename,
                "size": len(jpeg_bytes),
                "next_refresh_s": next_refresh_s,
            }

        hass.services.async_register(
            DOMAIN,
            "generate_device_panel_screen",
            handle_generate_device_panel_screen,
            schema=DEVICE_PANEL_SERVICE_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )

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
