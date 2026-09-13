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

    # Forecast is exposed as a state attribute for Lovelace/dashboard compatibility
    assert "forecast" in state.attributes
    assert isinstance(state.attributes["forecast"], list)


async def test_weather_cloud_coverage_is_converted_from_octas(
    hass: HomeAssistant, mock_smhi_api
) -> None:
    """SMHI reports cloudiness in octas; Home Assistant wants a percentage.

    The two differ by a factor of 12.5, not 10, and getting it wrong produces
    a number that looks entirely plausible — 4 octas reported as 40% rather
    than 50%. Worth pinning.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "Home", "latitude": 59.3293, "longitude": 18.0686},
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("weather.home")
    assert state
    # 4 octas is half the sky.
    assert state.attributes["cloud_coverage"] == 50
    assert state.attributes["visibility"] == 22.6
    # Gusts are converted to km/h by Home Assistant, as the wind speed is.
    assert state.attributes["wind_gust_speed"] == 32.4


async def test_weather_survives_a_forecast_without_the_new_fields(
    hass: HomeAssistant, mock_smhi_api
) -> None:
    """An older cached forecast has no cloud or visibility. Report nothing.

    The properties must return None rather than raising or inventing a zero —
    a missing measurement is not a clear sky.
    """
    mock_smhi_api.return_value["timeSeries"][0]["data"].pop("cloud_area_fraction")
    mock_smhi_api.return_value["timeSeries"][0]["data"].pop("visibility_in_air")

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "Home", "latitude": 59.3293, "longitude": 18.0686},
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("weather.home")
    assert state
    assert state.attributes.get("cloud_coverage") is None
    assert state.attributes.get("visibility") is None
