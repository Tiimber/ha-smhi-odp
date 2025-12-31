import logging
from datetime import timedelta
from homeassistant.util import dt as dt_util

# --- FIX: Import 'callback' ---
from homeassistant.core import callback
# --- END FIX ---

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfPressure,
    UnitOfSpeed,
    DEGREE,
)

# This import now correctly references the smhi_odp domain
from .const import DOMAIN, ATTRIBUTION

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the SMHI ODP sensor platform."""
    #_LOGGER.warning("SMHI_ODP: sensor.py async_setup_entry CALLED.")

    try:
        # Get the coordinator from hass.data
        coordinator = hass.data[DOMAIN][entry.entry_id]
        
        #_LOGGER.warning("SMHI_ODP: Coordinator successfully retrieved in sensor.py.")

        # Create sensor entities
        sensors_to_add = [
            # --- Current Condition Sensors ---
            SmhiTemperatureSensor(coordinator, entry),
            SmhiHumiditySensor(coordinator, entry),
            SmhiWindSpeedSensor(coordinator, entry),
            SmhiWindDirectionSensor(coordinator, entry),
            SmhiPressureSensor(coordinator, entry),
            SmhiPrecipitationSensor(coordinator, entry),
        ]
        
        #_LOGGER.warning("SMHI_ODP: Creating current condition sensors...")

        # --- Daily Forecast Sensors ---
        # Add 10 daily forecast sensors (Today, Tomorrow, +2, ... +9)
        #_LOGGER.warning("SMHI_ODP: Entering loop to create 10 daily sensors...")
        for i in range(10):
            #_LOGGER.warning(f"SMHI_ODP: Loop {i}: Creating SmhiDailyForecastSensor({i})")
            sensors_to_add.append(SmhiDailyForecastSensor(coordinator, entry, i))
            #_LOGGER.warning(f"SMHI_ODP: Loop {i}: Successfully appended sensor.")
            
        async_add_entities(sensors_to_add)

    except Exception as e:
        _LOGGER.error(f"SMHI_ODP: Error in sensor.py async_setup_entry: {e}", exc_info=True)


class SmhiBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for SMHI ODP sensors."""

    def __init__(self, coordinator, entry, name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        # self._name is set in the child class (e.g., "Temperature")
        self._name = name
        
        # Get the name from the config entry (e.g., "home")
        config_name = entry.data.get(CONF_NAME)
        
        # Set the entity name (e.g., "Temperature")
        self._attr_name = name
        
        # *** FIX ***
        # This line prepends the device name to the entity name,
        # which fixes the entity ID generation.
        self._attr_has_entity_name = True
        
        # Set the unique ID (e.g., "entry_id_temperature")
        self._attr_unique_id = f"{entry.entry_id}_{name.lower().replace(' ', '_')}"
        
        # Link to the device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            # Use the config name for the device (e.g., "SMHI ODP (home)")
            "name": f"SMHI ODP ({config_name})",
            "manufacturer": "SMHI",
            "model": "ODP Forecast",
            "entry_type": "service",
        }
        self._attr_attribution = ATTRIBUTION

    @property
    def current_data(self):
        """
        Helper to get the data for the current time entry.
        """
        try:
            # Add checks to prevent crash if data is missing
            if not self.coordinator.data:
                #_LOGGER.debug("Coordinator has no data")
                return None
            
            time_series = self.coordinator.data.get("timeSeries")
            if not time_series or len(time_series) == 0:
                #_LOGGER.debug("API returned no timeSeries")
                return None
            
            # This is the data object: {"air_temperature": 10.5, ...}
            return time_series[0].get("data")
        
        except (IndexError, KeyError, TypeError) as err:
            #_LOGGER.warning("Error parsing SMHI data: %s", err)
            return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # An entity is available if the coordinator updated successfully
        # and the current_data helper returns a valid dict.
        return super().available and self.coordinator.data is not None


# --- Current Condition Sensors ---

class SmhiTemperatureSensor(SmhiBaseSensor):
    """Representation of an SMHI ODP Temperature Sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Temperature")
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.current_data:
            return self.current_data.get("air_temperature")
        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self.current_data:
            # Return all other data points as attributes
            # This copies the whole dictionary of data
            return self.current_data
        return {}

class SmhiHumiditySensor(SmhiBaseSensor):
    """Representation of an SMHI ODP Humidity Sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Humidity")
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.current_data:
            return self.current_data.get("relative_humidity")
        return None


class SmhiWindSpeedSensor(SmhiBaseSensor):
    """Representation of an SMHI ODP Wind Speed Sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Wind Speed")
        self._attr_native_unit_of_measurement = UnitOfSpeed.METERS_PER_SECOND
        self._attr_device_class = SensorDeviceClass.WIND_SPEED
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.current_data:
            return self.current_data.get("wind_speed")
        return None


class SmhiWindDirectionSensor(SmhiBaseSensor):
    """Representation of an SMHI ODP Wind Direction Sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Wind Direction")
        self._attr_native_unit_of_measurement = DEGREE
        # Wind direction doesn't have a device_class in current HA versions

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.current_data:
            return self.current_data.get("wind_from_direction")
        return None


class SmhiPressureSensor(SmhiBaseSensor):
    """Representation of an SMHI ODP Pressure Sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Pressure")
        self._attr_native_unit_of_measurement = UnitOfPressure.HPA
        self._attr_device_class = SensorDeviceClass.ATMOSPHERIC_PRESSURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.current_data:
            return self.current_data.get("air_pressure_at_mean_sea_level")
        return None


class SmhiPrecipitationSensor(SmhiBaseSensor):
    """Representation of an SMHI ODP Precipitation Sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry, "Precipitation")
        self._attr_native_unit_of_measurement = "mm" # kg/m2 is equivalent to mm
        self._attr_device_class = SensorDeviceClass.PRECIPITATION
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.current_data:
            return self.current_data.get("precipitation_amount_mean")
        return None


# --- Daily Forecast Sensor ---

class SmhiDailyForecastSensor(SmhiBaseSensor):
    """Representation of an SMHI ODP Daily Forecast Sensor."""

    def __init__(self, coordinator, entry, day_offset):
        """Initialize the daily forecast sensor."""
        self._day_offset = day_offset
        
        # Set the name (e.g., "Today", "Tomorrow", "Day +2")
        if day_offset == 0:
            name = "Today"
        elif day_offset == 1:
            name = "Tomorrow"
        else:
            name = f"Day +{day_offset}"
            
        super().__init__(coordinator, entry, name)
        
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        
        # Store data for this day
        self._max_temp = None
        self._max_temp_data = {}

        #_LOGGER.warning(f"SMHI_ODP: Initializing daily sensor: {self._name}")

        # --- FIX REMOVED ---
        # Removed manual listener: self.coordinator.async_add_listener(self._handle_coordinator_update)
        # We will rely on the base CoordinatorEntity to set up the listener in async_added_to_hass
        # --- END FIX REMOVED ---

    # --- NEW DEBUGGING METHOD ---
    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        #_LOGGER.warning(f"SMHI_ODP: async_added_to_hass CALLED for {self._name}")
        # Call the base CoordinatorEntity's method which adds the listener
        await super().async_added_to_hass()
        #_LOGGER.warning(f"SMHI_ODP: super().async_added_to_hass() COMPLETED for {self._name}")
    # --- END NEW DEBUGGING METHOD ---

    @property
    def native_value(self):
        """Return the state of the sensor (max temp for the day)."""
        return self._max_temp

    @property
    def extra_state_attributes(self):
        """Return the state attributes (all data for the max temp time)."""
        # --- FIX: Added underscore to match the variable in __init__ ---
        return self._max_temp_data
        
    def _find_daily_max_temp(self):
        """
        Parses the full timeSeries to find the max temp for the specific day offset.
        This is called by the _handle_coordinator_update method.
        """
        try:
            if not self.coordinator.data:
                #_LOGGER.warning(f"[{self._name}] No coordinator data, clearing max temp")
                self._max_temp = None
                self._max_temp_data = {}
                return
                
            time_series = self.coordinator.data.get("timeSeries")
            if not time_series:
                #_LOGGER.warning(f"[{self._name}] No timeSeries in coordinator data, clearing max temp")
                self._max_temp = None
                self._max_temp_data = {}
                return
                
            # *** FIX: Use local timezone for all date comparisons ***
            
            # --- FIX: Use dt_util.now() with no args to get default HA timezone object ---
            # Get the current time in Home Assistant's configured timezone
            now_local = dt_util.now()
            start_of_today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Calculate the start and end of the target day
            target_day_start = start_of_today_local + timedelta(days=self._day_offset)
            target_day_end = target_day_start + timedelta(days=1)
            
            #_LOGGER.warning(f"[{self._name}] Finding max temp for day_offset {self._day_offset}")
            # --- FIX: Corrected variable name from target_key_end to target_day_start ---
            #_LOGGER.warning(f"[{self._name}] Target day start (local): {target_day_start}")
            #_LOGGER.warning(f"[{self._name}] Target day end (local): {target_day_end}")

            # --- NEW DEBUG LOG ---
            #_LOGGER.warning(f"[{self._name}] Current HA time (local): {now_local}")
            #_LOGGER.warning(f"[{self._name}] Total timeSeries entries: {len(time_series)}")
            # --- END DEBUG LOG ---

            max_temp = -float('inf')
            max_temp_entry_data = None
            
            # --- NEW DEBUG LOG ---
            # Add a counter for loop logging
            loop_counter = 0
            # --- END DEBUG LOG ---
            
            # Find the max temperature in the time entries for the target day
            for entry in time_series:
                # --- NEW DEBUG LOG ---
                loop_counter += 1
                # --- END DEBUG LOG ---
                
                # Parse the entry time (it's in UTC)
                entry_time_utc = dt_util.parse_datetime(entry["time"])
                if not entry_time_utc:
                    #_LOGGER.warning(f"[{self._name}] ERROR: FAILED to parse entry time: {entry.get('time')}")
                    continue

                # Check if this entry is within our target day
                # Python's aware datetime objects handle the timezone comparison
                if target_day_start <= entry_time_utc < target_day_end:
                    data = entry.get("data")
                    if not data:
                        continue
                        
                    temp = data.get("air_temperature")
                    if temp is not None:
                        # Log the first found entry as a debug message
                        # --- SYNTAX FIX: Changed self... to self._name ---
                        #_LOGGER.warning(f"[{self._name}] MATCH: Entry {entry_time_utc} (UTC) is in range. Temp: {temp}")
                        # --- END DEBUG LEVEL ---
                        if temp > max_temp:
                            max_temp = temp
                            max_temp_entry_data = data
                    #else:
                    #    _LOGGER.warning(f"[{self._name}] MATCH: Entry {entry_time_utc} (UTC) is in range, but 'air_temperature' is missing or None.")
                #else:
                #    # Log the first 5 entries that *don't* match
                #    if loop_counter <= 5:
                #        _LOGGER.warning(
                #            f"[{self._name}] REJECT: Entry {entry_time_utc} (UTC) is NOT in range "
                #            f"({target_day_start} to {target_day_end})"
                #        )

            if max_temp_entry_data:
                #_LOGGER.warning(f"[{self._name}] SUCCESS: Setting max temp to {max_temp}")
                self._max_temp = max_temp
                self._max_temp_data = max_temp_entry_data
            else:
                # No data found for this day
                #_LOGGER.warning(f"[{self._name}] FAILED: No matching entries found. Clearing max temp.")
                self._max_temp = None
                self._max_temp_data = {}

        except Exception as err:
            #_LOGGER.warning(f"Error parsing daily forecast data for {self._name}: {err}", exc_info=True)
            self._max_temp = None
            self._max_temp_data = {}

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # This sensor is available if the coordinator has data
        return super().available and self.coordinator.data is not None

    # --- FIX: Add @callback decorator ---
    @callback
    # --- END FIX ---
    # --- SYNTAX FIX: Removed erroneous 'f' ---
    # --- SYNTAX FIX: Removed erroneous 'Main' ---
    def _handle_coordinator_update(self) -> None:
        """
        Handle updated data from the coordinator.
        This is called by the CoordinatorEntity base class.
        """
        # --- NEW DEBUG LOG: Wrap in try/except to catch all errors ---
        #_LOGGER.warning(f"SMHI_ODP: _handle_coordinator_update ENTERED for {self._name}")
        try:
            # --- NEW DEBUG LOG ---
            #_LOGGER.warning(f"SMHI_ODP: Handling coordinator update for {self._name}")
            # --- END DEBUG LOG ---
            
            # Find the max temp for this sensor's day
            # --- FIX: Added parentheses to call the method ---
            self._find_daily_max_temp()
            
            self.async_write_ha_state()
            #_LOGGER.warning(f"SMHI_ODP: _handle_coordinator_update EXITED for {self._name}")
            
        except Exception as e:
            _LOGGER.error(f"SMHI_ODP: CRITICAL ERROR in _handle_coordinator_update for {self._name}: {e}", exc_info=True)