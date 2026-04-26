"""The SMHI ODP integration."""

import logging
from datetime import timedelta
import httpx
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import httpx_client, config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    Platform,
)

# This import must match your folder name and const.py
from .const import DOMAIN
from .display_service import WeatherDisplayService
from .awtrix_service import AwtrixWeatherService

_LOGGER = logging.getLogger(__name__)

# Service schema
SERVICE_SCHEMA = vol.Schema(
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
            raise UpdateFailed(
                f"Connection error fetching data from SMHI: {err}"
            ) from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMHI ODP from a config entry."""

    # _LOGGER.warning("SMHI_ODP: Setting up config entry.")

    # Create the coordinator
    coordinator = SmhiDataUpdateCoordinator(hass, entry)

    # Fetch initial data so we have it when platforms are set up
    # _LOGGER.warning("SMHI_ODP: Performing first data refresh...")
    await coordinator.async_config_entry_first_refresh()
    # _LOGGER.warning("SMHI_ODP: First data refresh complete.")

    # Store the coordinator in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Create display service if not already created
    if "display_service" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["display_service"] = WeatherDisplayService()
    
    # Create AWTRIX service if not already created
    if "awtrix_service" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["awtrix_service"] = AwtrixWeatherService()

    # Register services (only once for the domain)
    if not hass.services.has_service(DOMAIN, "generate_today_gif"):

        async def handle_generate_today_gif(call: ServiceCall):
            """Handle the generate_today_gif service call."""
            entry_id = call.data.get("entry_id", entry.entry_id)
            coord = hass.data[DOMAIN].get(entry_id)
            if not coord:
                _LOGGER.error(f"No coordinator found for entry_id: {entry_id}")
                return {"success": False, "error": "No coordinator found"}

            display_service = hass.data[DOMAIN]["display_service"]
            gif_bytes = await display_service.generate_today_gif(coord, entry)

            # Save directly to /config/www/
            filename = "weather_today.gif"
            filepath = hass.config.path("www", filename)

            def write_file():
                with open(filepath, "wb") as f:
                    f.write(gif_bytes)

            await hass.async_add_executor_job(write_file)
            _LOGGER.info(f"Saved {filename}: {len(gif_bytes)} bytes")
            return {"success": True, "filename": filename, "size": len(gif_bytes)}

        async def handle_generate_tomorrow_gif(call: ServiceCall):
            """Handle the generate_tomorrow_gif service call."""
            entry_id = call.data.get("entry_id", entry.entry_id)
            coord = hass.data[DOMAIN].get(entry_id)
            if not coord:
                _LOGGER.error(f"No coordinator found for entry_id: {entry_id}")
                return {"success": False, "error": "No coordinator found"}

            display_service = hass.data[DOMAIN]["display_service"]
            gif_bytes = await display_service.generate_tomorrow_gif(coord, entry)

            # Save directly to /config/www/
            filename = "weather_tomorrow.gif"
            filepath = hass.config.path("www", filename)

            def write_file():
                with open(filepath, "wb") as f:
                    f.write(gif_bytes)

            await hass.async_add_executor_job(write_file)
            _LOGGER.info(f"Saved {filename}: {len(gif_bytes)} bytes")
            return {"success": True, "filename": filename, "size": len(gif_bytes)}

        async def handle_generate_week_gif(call: ServiceCall):
            """Handle the generate_week_gif service call."""
            entry_id = call.data.get("entry_id", entry.entry_id)
            coord = hass.data[DOMAIN].get(entry_id)
            if not coord:
                _LOGGER.error(f"No coordinator found for entry_id: {entry_id}")
                return {"success": False, "error": "No coordinator found"}

            display_service = hass.data[DOMAIN]["display_service"]
            gif_bytes = await display_service.generate_week_gif(coord, entry)

            # Save directly to /config/www/
            filename = "weather_week.gif"
            filepath = hass.config.path("www", filename)

            def write_file():
                with open(filepath, "wb") as f:
                    f.write(gif_bytes)

            await hass.async_add_executor_job(write_file)
            _LOGGER.info(f"Saved {filename}: {len(gif_bytes)} bytes")
            return {"success": True, "filename": filename, "size": len(gif_bytes)}

        hass.services.async_register(
            DOMAIN,
            "generate_today_gif",
            handle_generate_today_gif,
            schema=SERVICE_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )
        hass.services.async_register(
            DOMAIN,
            "generate_tomorrow_gif",
            handle_generate_tomorrow_gif,
            schema=SERVICE_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )
        hass.services.async_register(
            DOMAIN,
            "generate_week_gif",
            handle_generate_week_gif,
            schema=SERVICE_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )

        # AWTRIX animation services
        async def handle_get_current_weather(call: ServiceCall):
            """Handle the get_current_weather service call."""
            entry_id = call.data.get("entry_id", entry.entry_id)
            coord = hass.data[DOMAIN].get(entry_id)
            if not coord:
                _LOGGER.error(f"No coordinator found for entry_id: {entry_id}")
                return {"success": False, "error": "No coordinator found"}

            awtrix_service = hass.data[DOMAIN]["awtrix_service"]
            forecast_data = coord.data
            
            payload = await hass.async_add_executor_job(
                awtrix_service.generate_current_weather, forecast_data
            )
            
            _LOGGER.info(f"Generated current weather payload")
            return {"success": True, "payload": payload}

        async def handle_generate_today_awtrix(call: ServiceCall):
            """Handle the generate_today_awtrix service call."""
            entry_id = call.data.get("entry_id", entry.entry_id)
            coord = hass.data[DOMAIN].get(entry_id)
            if not coord:
                _LOGGER.error(f"No coordinator found for entry_id: {entry_id}")
                return {"success": False, "error": "No coordinator found"}

            awtrix_service = hass.data[DOMAIN]["awtrix_service"]
            forecast_data = coord.data
            
            frames = await hass.async_add_executor_job(
                awtrix_service.generate_today_animation, forecast_data, 6
            )
            
            _LOGGER.info(f"Generated {len(frames)} AWTRIX frames for today")
            return {"success": True, "frames": frames, "count": len(frames)}

        async def handle_generate_tomorrow_awtrix(call: ServiceCall):
            """Handle the generate_tomorrow_awtrix service call."""
            entry_id = call.data.get("entry_id", entry.entry_id)
            coord = hass.data[DOMAIN].get(entry_id)
            if not coord:
                _LOGGER.error(f"No coordinator found for entry_id: {entry_id}")
                return {"success": False, "error": "No coordinator found"}

            awtrix_service = hass.data[DOMAIN]["awtrix_service"]
            forecast_data = coord.data
            
            frames = await hass.async_add_executor_job(
                awtrix_service.generate_tomorrow_animation, forecast_data
            )
            
            _LOGGER.info(f"Generated {len(frames)} AWTRIX frames for tomorrow")
            return {"success": True, "frames": frames, "count": len(frames)}

        async def handle_generate_week_awtrix(call: ServiceCall):
            """Handle the generate_week_awtrix service call."""
            entry_id = call.data.get("entry_id", entry.entry_id)
            coord = hass.data[DOMAIN].get(entry_id)
            if not coord:
                _LOGGER.error(f"No coordinator found for entry_id: {entry_id}")
                return {"success": False, "error": "No coordinator found"}

            awtrix_service = hass.data[DOMAIN]["awtrix_service"]
            forecast_data = coord.data
            
            frames = await hass.async_add_executor_job(
                awtrix_service.generate_week_animation, forecast_data, 7
            )
            
            _LOGGER.info(f"Generated {len(frames)} AWTRIX frames for week")
            return {"success": True, "frames": frames, "count": len(frames)}

        hass.services.async_register(
            DOMAIN,
            "get_current_weather",
            handle_get_current_weather,
            schema=SERVICE_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
        hass.services.async_register(
            DOMAIN,
            "generate_today_awtrix",
            handle_generate_today_awtrix,
            schema=SERVICE_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
        hass.services.async_register(
            DOMAIN,
            "generate_tomorrow_awtrix",
            handle_generate_tomorrow_awtrix,
            schema=SERVICE_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
        hass.services.async_register(
            DOMAIN,
            "generate_week_awtrix",
            handle_generate_week_awtrix,
            schema=SERVICE_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # _LOGGER.warning("SMHI_ODP: Unloading config entry.")

    # Unload the sensor platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove the coordinator from hass.data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        # If no more entries, unregister services and cleanup
        remaining_entries = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id
        ]

        if not remaining_entries:
            hass.services.async_remove(DOMAIN, "generate_today_gif")
            hass.services.async_remove(DOMAIN, "generate_tomorrow_gif")
            hass.services.async_remove(DOMAIN, "generate_week_gif")
            hass.services.async_remove(DOMAIN, "get_current_weather")
            hass.services.async_remove(DOMAIN, "generate_today_awtrix")
            hass.services.async_remove(DOMAIN, "generate_tomorrow_awtrix")
            hass.services.async_remove(DOMAIN, "generate_week_awtrix")

            if "display_service" in hass.data[DOMAIN]:
                hass.data[DOMAIN].pop("display_service")
            if "awtrix_service" in hass.data[DOMAIN]:
                hass.data[DOMAIN].pop("awtrix_service")

    return unload_ok
