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

    # Check wind speed (HA converts m/s to km/h: 5.0 * 3.6 = 18.0)
    state = hass.states.get("sensor.smhi_odp_home_wind_speed")
    assert state
    assert state.state == "18.0"  # HA converts to km/h


async def test_cloud_base_sensor(hass: HomeAssistant, mock_smhi_api) -> None:
    """Cloud base is published in metres, as its own sensor.

    Home Assistant has no standard weather-entity property for it, and it is
    the difference between low stratus on the hills and high cirrus.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "Home", "latitude": 59.3293, "longitude": 18.0686},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.smhi_odp_home_cloud_base")
    assert state
    assert float(state.state) == 841
    assert state.attributes["unit_of_measurement"] == "m"
    assert state.attributes["device_class"] == "distance"


async def test_cloud_base_reports_nothing_when_there_is_no_cloud(
    hass: HomeAssistant, mock_smhi_api
) -> None:
    """A clear sky has no cloud base. Report nothing, never zero.

    SMHI uses a negative value for "not applicable", and zero would claim the
    cloud is sitting on the ground.
    """
    mock_smhi_api.return_value["timeSeries"][0]["data"]["cloud_base_altitude"] = -9

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "Home", "latitude": 59.3293, "longitude": 18.0686},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.smhi_odp_home_cloud_base")
    assert state
    assert state.state in ("unknown", "unavailable")


async def test_cloud_base_rejects_the_9999_sentinel(
    hass: HomeAssistant, mock_smhi_api
) -> None:
    """🛑 SMHI uses 9999 for "no value", and it appears even under full cloud.

    Observed live: a forecast hour reporting eight octas of cloud and a base of
    9999. Passing that through would put the cloud layer ten kilometres up.
    """
    mock_smhi_api.return_value["timeSeries"][0]["data"]["cloud_base_altitude"] = 9999

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "Home", "latitude": 59.3293, "longitude": 18.0686},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.smhi_odp_home_cloud_base")
    assert state
    assert state.state in ("unknown", "unavailable")
