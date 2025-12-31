"""Test the SMHI ODP config flow."""
from unittest.mock import patch
import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.smhi_odp.const import DOMAIN

async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "custom_components.smhi_odp.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Home",
                "latitude": 59.3293,
                "longitude": 18.0686,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Home"
    assert result2["data"] == {
        "name": "Home",
        "latitude": 59.3293,
        "longitude": 18.0686,
    }
    assert len(mock_setup_entry.mock_calls) == 1
