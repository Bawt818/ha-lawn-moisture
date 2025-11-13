"""DataUpdateCoordinator for integration_blueprint."""

from __future__ import annotations

import math
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .const import (
    DEW_MOIST_CAP,
    DEW_TEMP_DIFFERENCE,
    DOMAIN,
    HUMIDITY_THRESHOLD,
    LOGGER,
    MASTER_DRYING_COEFFICIENT,
    MAX_DRYING_TEMP_C,
    MAX_EFFECTIVE_WIND_KMH,
    MAX_SOLAR_POWER_W,
    MIN_DRYING_TEMP_C,
    WEIGHTS,
    WETTING_INCREMENT,
)


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
            sun_power = self.hass.states.get("sensor.solar_total_power")
            weather_state = self.hass.states.get("weather.forecast_home_2")
            attributes_dict = weather_state.attributes
            wind_speed = attributes_dict.get("wind_speed", 0)

            # (Error checking here in case sensors are 'unavailable')
            try:
                wind = float(wind_speed)
            except (TypeError, ValueError):
                # Handle case where the value might be 'unknown' or 'None'
                wind = 0.0
            temp = float(temp_state.state)
            humidity = float(humidity_state.state)
            is_raining = rain_state.state == 1
            is_daytime = sun_state.state == "above_horizon"
            try:
                solar = float(sun_power.state)
            except (TypeError, ValueError):
                solar = 0.0


            # --- 1. Calculate Dew Point ---
            dew_point = calculate_dew_point(temp, humidity)
            dew_point_depression = temp - dew_point # How close are we to 100%?

            # --- 2. Calculate Drying via Evaporation ---
            dry_rate = calculate_grass_drying(
                solar,
                humidity,
                temp,
                wind,
            )

            # --- 3. Run the Model Logic ---
            current_moisture = self.moisture_level

            # A. Handle Rain (Resets everything)
            if is_raining:
                current_moisture = 1.0

            # B. Handle Wetting (Dew at Night)
            elif (
                not is_daytime
                and humidity > HUMIDITY_THRESHOLD
                and current_moisture < DEW_MOIST_CAP
                and dew_point_depression < DEW_TEMP_DIFFERENCE
            ):
                # It's a dewy night. Add a small amount.
                dew_increase = WETTING_INCREMENT
                current_moisture = min(current_moisture + dew_increase, DEW_MOIST_CAP)

            # C. Handle Drying (Daytime)
            elif is_daytime and humidity < HUMIDITY_THRESHOLD:
                current_moisture = max(0.0, current_moisture - dry_rate)

            # --- 4. Save the new state ---
            self.moisture_level = round(current_moisture, 3)

        except Exception as e:
            msg = f"Error updating data: {e}"
            raise UpdateFailed(msg) from e
        else:
            # --- 5. Return the data for sensors to use ---
            return {
                "moisture": self.moisture_level,
                "dew_point": dew_point,
            }


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

    return (B * gamma) / (A - gamma)


def calculate_grass_drying(
        solar_power: float,
        humidity: float,
        temperature: float,
        wind_speed: float
        ) -> float:
    """
    Calculate the new grass wetness level after accounting for evaporation.

    Args:
        solar_power (float): Current solar power in Watts.
        humidity (float): Current relative outside humidity as a percentage (0-100).
        temperature (float): Current outside temperature in Celsius.
        wind_speed (float): Current wind speed in km/h.

    Returns:
        float: The new, lower wetness score, clamped between 0.0 and 1.0.

    """
    # --- Step 1: Calculate individual factor components (0.0 to 1.0) ---

    # Sun Component: More sun = more drying. Linear scale.
    sun_component = max(0.0, min(1.0, solar_power / MAX_SOLAR_POWER_W)) # Clamp it

    # Humidity Component: Less humidity = more drying. This is an inverse relationship.
    humidity_component = (90.0 - humidity) / 100.0 # No drying above 90% humidity
    humidity_component = max(0.0, min(1.0, humidity_component))

    # Temperature Component: Warmer is better. Scaled between min and max temps.
    temp_range = MAX_DRYING_TEMP_C - MIN_DRYING_TEMP_C
    temp_component = (temperature - MIN_DRYING_TEMP_C) / temp_range
    temp_component = max(0.0, min(1.0, temp_component))

    # Wind Component: More wind = more drying, up to a certain point.
    wind_component = wind_speed / MAX_EFFECTIVE_WIND_KMH
    wind_component = max(0.0, min(1.0, wind_component))

    # --- Step 2: Calculate the total drying potential using weights ---

    # Multiply the two "limiting factors" to get the base potential.
    base_drying_potential = sun_component * humidity_component

    # Calculate the boost from "accelerant factors" (temp and wind).
    # Starts at 1.0 (no boost) and increases with favorable conditions.
    accelerant_boost = (
        1.0
        + (temp_component * WEIGHTS["temperature"])
        + (wind_component * WEIGHTS["wind"])
    )

    return base_drying_potential * accelerant_boost * MASTER_DRYING_COEFFICIENT
