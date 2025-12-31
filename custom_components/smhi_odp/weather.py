"""Support for SMHI ODP weather service."""
from datetime import datetime, timedelta
import logging

from homeassistant.components.weather import (
    WeatherEntity,
    WeatherEntityFeature,
    ForecastV2Daily,
)
from homeassistant.const import (
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, ATTRIBUTION

_LOGGER = logging.getLogger(__name__)

# SMHI Wsymb2 code mapping to HA conditions
CONDITION_CLASSES = {
    "clear-night": [1],  # Clear sky
    "sunny": [1, 2],     # Clear sky, Nearly clear sky
    "partlycloudy": [3, 4], # Variable cloudiness, Halfclear sky
    "cloudy": [5, 6],    # Cloudy sky, Overcast
    "fog": [7],          # Fog
    "rainy": [8, 9, 10, 18, 19, 20], # Light rain showers, Moderate rain showers, Heavy rain showers, Light rain, Moderate rain, Heavy rain
    "lightning-rainy": [11, 21], # Thunderstorm, Thunder
    "snowy-rainy": [12, 13, 14, 22, 23, 24], # Light sleet showers, Moderate sleet showers, Heavy sleet showers, Light sleet, Moderate sleet, Heavy sleet
    "snowy": [15, 16, 17, 25, 26, 27], # Light snow showers, Moderate snow showers, Heavy snow showers, Light snowfall, Moderate snowfall, Heavy snowfall
}

async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the SMHI weather platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SmhiWeather(coordinator, entry)], False)


class SmhiWeather(CoordinatorEntity, WeatherEntity):
    """Representation of a weather entity."""

    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_visibility_unit = UnitOfLength.KILOMETERS
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_attribution = ATTRIBUTION
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY

    def __init__(self, coordinator, entry) -> None:
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self._attr_name = entry.data.get("name", "SMHI")
        self._attr_unique_id = f"{entry.entry_id}_weather"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"SMHI ODP ({self._attr_name})",
            "manufacturer": "SMHI",
            "model": "ODP Forecast",
            "entry_type": "service",
        }

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        if not self.coordinator.data:
            return None
            
        # Get the symbol from the first time series entry
        time_series = self.coordinator.data.get("timeSeries")
        if not time_series:
            return None
            
        symbol = time_series[0]["data"].get("weather_symbol")
        return next(
            (k for k, v in CONDITION_CLASSES.items() if symbol in v),
            None,
        )

    @property
    def native_temperature(self) -> float | None:
        """Return the temperature."""
        return self._get_current_data("air_temperature")

    @property
    def native_pressure(self) -> float | None:
        """Return the pressure."""
        return self._get_current_data("air_pressure_at_mean_sea_level")

    @property
    def humidity(self) -> float | None:
        """Return the humidity."""
        return self._get_current_data("relative_humidity")

    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed."""
        return self._get_current_data("wind_speed")

    @property
    def wind_bearing(self) -> float | None:
        """Return the wind bearing."""
        return self._get_current_data("wind_from_direction")

    def _get_current_data(self, key):
        """Helper to get current data."""
        if self.coordinator.data and self.coordinator.data.get("timeSeries"):
            return self.coordinator.data["timeSeries"][0]["data"].get(key)
        return None

    async def async_forecast_daily(self) -> list[ForecastV2Daily] | None:
        """Return the daily forecast in native units."""
        if not self.coordinator.data:
            return None

        time_series = self.coordinator.data.get("timeSeries")
        if not time_series:
            return None

        forecast_data = []
        processed_days = set()
        
        now = dt_util.now()
        today = now.date()

        for entry in time_series:
            entry_time = dt_util.parse_datetime(entry["time"])
            if not entry_time:
                continue
                
            entry_date = entry_time.date()
            
            # Skip past data, but include today
            if entry_date < today:
                continue

            # We want one entry per day, ideally around noon (12:00) to represent the day
            # simpler approach: aggregate max temp for the day, and use noon symbol
            if entry_date not in processed_days:
                # Find noon entry for symbol, fallback to current entry
                noon_entry = self._find_noon_entry(time_series, entry_date)
                day_data = noon_entry["data"] if noon_entry else entry["data"]
                
                # Find max temp for the day
                max_temp = self._get_daily_max_temp(time_series, entry_date)
                min_temp = self._get_daily_min_temp(time_series, entry_date) # Added min temp

                symbol = day_data.get("weather_symbol")
                condition = next(
                    (k for k, v in CONDITION_CLASSES.items() if symbol in v),
                    None,
                )

                forecast_data.append(
                    ForecastV2Daily(
                        datetime=entry_date.isoformat(),
                        native_temperature=max_temp,
                        native_templow=min_temp,
                        condition=condition,
                        native_precipitation=day_data.get("precipitation_amount_mean", 0) * 24, # Rough daily estimate
                        wind_bearing=day_data.get("wind_from_direction"),
                        native_wind_speed=day_data.get("wind_speed"),
                    )
                )
                processed_days.add(entry_date)
                
                # Limit to 10 days
                if len(forecast_data) >= 10:
                    break

        return forecast_data

    def _find_noon_entry(self, time_series, date):
        """Find the entry closest to 12:00 for a given date."""
        target_time = datetime.combine(date, datetime.min.time().replace(hour=12)).replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        
        best_entry = None
        min_diff = float("inf")

        for entry in time_series:
            entry_time = dt_util.parse_datetime(entry["time"])
            if entry_time.date() == date:
                # Naive comparison is okay here as both should be valid
                diff = abs((entry_time - target_time).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    best_entry = entry
        
        return best_entry

    def _get_daily_max_temp(self, time_series, date):
        """Find max temperature for a given date."""
        max_temp = -float("inf")
        found = False
        for entry in time_series:
            entry_time = dt_util.parse_datetime(entry["time"])
            if entry_time.date() == date:
                temp = entry["data"].get("air_temperature")
                if temp is not None:
                    if temp > max_temp:
                        max_temp = temp
                        found = True
        return max_temp if found else None

    def _get_daily_min_temp(self, time_series, date):
        """Find min temperature for a given date."""
        min_temp = float("inf")
        found = False
        for entry in time_series:
            entry_time = dt_util.parse_datetime(entry["time"])
            if entry_time.date() == date:
                temp = entry["data"].get("air_temperature")
                if temp is not None:
                    if temp < min_temp:
                        min_temp = temp
                        found = True
        return min_temp if found else None
