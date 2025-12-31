"""Test component setup."""
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.core import HomeAssistant
from custom_components.smhi_odp.const import DOMAIN

async def test_async_setup_entry(hass: HomeAssistant, mock_smhi_api) -> None:
    """Test a successful setup entry."""
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

    assert entry.state == "loaded"
    assert "smhi_odp" in hass.data
    assert entry.entry_id in hass.data["smhi_odp"]

    # Test unload
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    
    assert entry.state == "not_loaded"
    # Ensure it's removed from data (except if integration leaves empty dict, but standard is to clean up)
    # Based on our __init__.py code: hass.data[DOMAIN].pop(entry.entry_id)
    assert entry.entry_id not in hass.data.get("smhi_odp", {})
