"""Test SMHI weather entity."""
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.core import HomeAssistant
from custom_components.smhi_odp.const import DOMAIN

async def test_weather_entity(hass: HomeAssistant, mock_smhi_api) -> None:
    """Test weather entity state and attributes."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Home",
            "latitude": 59.3293,
            "longitude": 18.0686,
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Check weather entity state
    # Entity ID should be weather.smhi_odp_home
    state = hass.states.get("weather.smhi_odp_home")
    assert state
    assert state.state == "sunny"  # Mapped from symbol 1
    
    # Check attributes
    assert state.attributes["temperature"] == 15.0
    assert state.attributes["humidity"] == 60.0
    assert state.attributes["pressure"] == 1012.0
    assert state.attributes["wind_speed"] == 5.0

    # Ensure forecast service is callable (HA 2024.x style or attribute check)
    # The integration implements persistent forecast or on-demand.
    # We checked implementation: it uses `async_forecast_daily` and supports `FORECAST_DAILY`.
    # Modern HA doesn't put forecast in attributes by default unless using older pattern, 
    # but `WeatherEntity` might still cache it if subscribed.
    # Let's just check the state for now.
