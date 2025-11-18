"""Constants for integration_blueprint."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "moisture_tracker"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"
PLATFORMS: list[str] = ["sensor"]

# --- MODEL TUNING CONSTANTS ---
# Wetting
HUMIDITY_THRESHOLD: float = 85.0
DEW_TEMP_DIFFERENCE: float = 1.0  # (temp - dew_point)
DEW_MOIST_CAP: float = 0.6  # (60%)
DEW_RESET_HOUR: int = 12

# Increments
WETTING_INCREMENT: float = 0.1

# 1. Master Drying Coefficient: The overall speed of evaporation.
# A higher value means the grass dries faster in ideal conditions.
MASTER_DRYING_COEFFICIENT: float = 0.02

# 2. Component Weights: How much each factor contributes to the drying process.
WEIGHTS = {
    "temperature": 0.15,  # Warmth helps.
    "wind": 0.10,  # Wind helps.
}

# 3. Sensor Normalization Ranges: Define the expected "min" and "max" for your sensors
# to scale them to a 0.0-1.0 factor.
# - Set MAX_SOLAR_POWER to the typical maximum wattage your panels produce.
# - Set temperatures for a reasonable range where drying occurs.
# - Set wind speed for a range where it has a meaningful effect.
MAX_SOLAR_POWER_W: float = 6000  # Watts
MIN_DRYING_TEMP_C: float = 8  # Drying is negligible below this temp
MAX_DRYING_TEMP_C: float = 30  # At this temp, the contribution is maxed out
MAX_EFFECTIVE_WIND_KMH: float = 30  # Wind speeds above this don't add much more effect
