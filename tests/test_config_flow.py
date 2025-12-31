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
    assert not result["errors"]

    # Mock the HTTP response for API validation
    with patch(
        "custom_components.smhi_odp.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry, patch(
        "custom_components.smhi_odp.config_flow.httpx_client.get_async_client"
    ) as mock_get_client:
        # Create a mock HTTP client that returns a successful response
        from unittest.mock import AsyncMock
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client
        
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "Home",
                "location": {
                    "latitude": 59.3293,
                    "longitude": 18.0686,
                },
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "SMHI ODP (Home)"
    assert result2["data"] == {
        "name": "Home",
        "latitude": 59.3293,
        "longitude": 18.0686,
    }
    assert len(mock_setup_entry.mock_calls) == 1

