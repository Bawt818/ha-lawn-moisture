"""DataUpdateCoordinator for integration_blueprint."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

import math



# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class MoistureDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching moisture data from the API."""
        
    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )        
        self.moisture_level: float = 0.5

    async def _async_update_data(self) -> dict:
        try:
            # --- Get Inputs from Home Assistant ---
            temp_state = self.hass.states.get("sensor.outside_temperature")
            humidity_state = self.hass.states.get("sensor.tsensor_outside_humidity")
            sun_state = self.hass.states.get("sun.sun")
            rain_state = self.hass.states.get("sensor.rain_sensor")

            # (Error checking here in case sensors are 'unavailable')
            temp = float(temp_state.state)
            humidity = float(humidity_state.state)
            is_raining = rain_state.state == 1
            is_daytime = sun_state.state == "above_horizon"
            
            # --- 1. Calculate Dew Point ---
            dew_point = calculate_dew_point(temp, humidity)
            dew_point_depression = temp - dew_point # How close are we to 100%?

            # --- 2. Run the Model Logic ---
            current_moisture = self.moisture_level

            # A. Handle Rain (Resets everything)
            if is_raining:
                current_moisture = 1.0

            # B. Handle Wetting (Dew at Night)
            elif not is_daytime and dew_point_depression < 2.0 and humidity > 90.0:
                # It's a dewy night. Add a small amount.
                dew_increase = 0.05 
                current_moisture = min(current_moisture + dew_increase, 0.6)

            # C. Handle Drying (Daytime)
            elif is_daytime and dew_point_depression > 5.0:
                # It's drying out. The 'dry_rate' can be a function
                # of how dry the air is (dew_point_depression).
                dry_rate = 0.01 * (dew_point_depression) 
                current_moisture = max(0.0, current_moisture - dry_rate)
            
            # --- 3. Save the new state ---
            self.moisture_level = round(current_moisture, 3)

            # --- 4. Return the data for sensors to use ---
            return {
                "moisture": self.moisture_level,
                "dew_point": dew_point,
            }
        except Exception as e:
            raise UpdateFailed(f"Error updating data: {e}") from e


# Constants for the Magnus-Tetens formula (for dew point)
A = 17.27
B = 237.7

def calculate_dew_point(temp_c: float, relative_humidity: float) -> float:
    """
    Calculate the dew point in Celsius using the Magnus-Tetens formula.
    
    :param temp_c: Current temperature in Celsius.
    :param relative_humidity: Current relative humidity as a percentage (e.g., 65.0).
    :return: Dew point in Celsius.
    """
    rh = relative_humidity / 100.0
    
    # Calculate the "gamma" value
    gamma = (A * temp_c) / (B + temp_c) + math.log(rh)
    
    # Calculate the dew point
    dew_point = (B * gamma) / (A - gamma)
    
    return dew_point
    