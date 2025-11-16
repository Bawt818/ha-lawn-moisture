"""Calculation functions for moisture tracker."""

from __future__ import annotations

import math

from .const import (
    MASTER_DRYING_COEFFICIENT,
    MAX_DRYING_TEMP_C,
    MAX_EFFECTIVE_WIND_KMH,
    MAX_SOLAR_POWER_W,
    MIN_DRYING_TEMP_C,
    WEIGHTS,
)

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
    solar_power: float, humidity: float, temperature: float, wind_speed: float
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
    sun_component = max(0.0, min(1.0, solar_power / MAX_SOLAR_POWER_W))  # Clamp it

    # Humidity Component: Less humidity = more drying. This is an inverse relationship.
    humidity_component = (90.0 - humidity) / 100.0  # No drying above 90% humidity
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
