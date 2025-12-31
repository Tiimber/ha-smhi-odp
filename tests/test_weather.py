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
    # Entity ID is weather.home (based on name)
    state = hass.states.get("weather.home")
    assert state
    assert state.state == "clear-night"  # Mapped from symbol 1
    
    # Check attributes (wind_speed is converted to km/h: 5.0 * 3.6 = 18.0)
    assert state.attributes["temperature"] == 15.0
    assert state.attributes["humidity"] == 60
    assert state.attributes["pressure"] == 1012.0
    assert state.attributes["wind_speed"] == 18.0  # HA converts to km/h

