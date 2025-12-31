"""Global fixtures for SMHI ODP integration."""
from unittest.mock import patch
import pytest

from custom_components.smhi_odp.const import DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield

@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield

@pytest.fixture(name="mock_smhi_api")
def mock_smhi_api_fixture():
    """Mock the SMHI API client."""
    with patch("custom_components.smhi_odp.SmhiDataUpdateCoordinator._async_update_data") as mock_update:
        # Return sensible default data
        mock_update.return_value = {
            "timeSeries": [
                {
                    "time": "2023-10-10T12:00:00Z",
                    "data": {
                        "air_temperature": 15.0,
                        "relative_humidity": 60.0,
                        "wind_speed": 5.0,
                        "wind_from_direction": 180.0,
                        "air_pressure_at_mean_sea_level": 1012.0,
                        "precipitation_amount_mean": 0.0,
                        "weather_symbol": 1, # Sunny/Clear
                    }
                }
            ]
        }
        yield mock_update
