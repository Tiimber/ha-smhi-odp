"""Config flow for SMHI ODP."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.helpers import httpx_client, selector as sel

# This import now correctly references the smhi_odp domain
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SmhiOdpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMHI ODP."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SmhiOdpOptionsFlow()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Get data from the form
            location_data = user_input["location"]
            name = user_input[CONF_NAME]
            lat = location_data[CONF_LATITUDE]
            lon = location_data[CONF_LONGITUDE]

            # Create a unique ID for this config entry
            await self.async_set_unique_id(f"{lat}-{lon}")
            self._abort_if_unique_id_configured()

            try:
                # Test the API connection
                await self._test_api_connection(lat, lon)
            except Exception as e:
                _LOGGER.error("SMHI ODP API connection error: %s", e)
                errors["base"] = "cannot_connect"
            
            if not errors:
                # Input is valid, create the config entry.
                # We save the name and location data together
                data_to_save = {
                    CONF_NAME: name,
                    **location_data
                }
                
                return self.async_create_entry(
                    title=f"SMHI ODP ({name})",
                    data=data_to_save, 
                )

        # Get default coordinates from Home Assistant's config
        default_lat = self.hass.config.latitude
        default_lon = self.hass.config.longitude

        # Create the schema with Name and Location Selector
        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default="home"): str,
                vol.Required(
                    "location",
                    default={
                        "latitude": default_lat,
                        "longitude": default_lon,
                    },
                ): sel.LocationSelector(),
            }
        )

        # Show the form to the user
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def _test_api_connection(self, lat, lon):
        """Test the API connection with SMHI."""
        client = httpx_client.get_async_client(self.hass)
        api_url = f"https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/{lon:.6f}/lat/{lat:.6f}/data.json"
        
        _LOGGER.debug("Connecting to SMHI ODP API at: %s", api_url)
        response = await client.get(api_url)
        _LOGGER.debug("API response status code: %s", response.status_code)
        response.raise_for_status()


class SmhiOdpOptionsFlow(config_entries.OptionsFlow):
    """Options for a SMHI ODP config entry.

    Currently just the opt-in toggle for the device panel image export
    (the generate_device_panel_screen service). Off by default, so the
    integration behaves exactly as before for anyone not using it.
    """

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get("enable_device_panel_export", False)
        data_schema = vol.Schema(
            {
                vol.Optional("enable_device_panel_export", default=current): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
