"""Test SMHI sensors."""
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.core import HomeAssistant
from custom_components.smhi_odp.const import DOMAIN

async def test_sensors(hass: HomeAssistant, mock_smhi_api) -> None:
    """Test we get sensor data."""
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

    # Check state of main temperature sensor
    # Note: Entity ID format logic in sensor.py: 
    # self._attr_unique_id = f"{entry.entry_id}_{name.lower().replace(' ', '_')}"
    # and has_entity_name=True, so it should be sensor.smhi_odp_home_temperature
    
    # Actually, HA generates the ID based on the name if has_entity_name is True.
    # The device name is "SMHI ODP (Home)" and entity name is "Temperature".
    # Typically this results in sensor.smhi_odp_home_temperature.
    # Let's verify against the logic.
    
    state = hass.states.get("sensor.smhi_odp_home_temperature")
    assert state
    assert state.state == "15.0"
    assert state.attributes["unit_of_measurement"] == "°C"

    # Check humidity
    state = hass.states.get("sensor.smhi_odp_home_humidity")
    assert state
    assert state.state == "60.0"

    # Check wind speed
    state = hass.states.get("sensor.smhi_odp_home_wind_speed")
    assert state
    assert state.state == "5.0"
