"""DataUpdateCoordinator for integration_blueprint."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, State

from .calculations import calculate_dew_point, calculate_grass_drying
from .const import (
    DEW_MOIST_CAP,
    DEW_RESET_HOUR,
    DEW_TEMP_DIFFERENCE,
    DOMAIN,
    HUMIDITY_THRESHOLD,
    LOGGER,
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
        # Store the moisture level between runs with self.
        self.moisture_level: float = 0.0

        self.sunset_temp: float | None = None
        self.sunset_humi: float | None = None

        # store the sunset values ONCE per day.
        self.has_stored_sunset_values: bool = False

    async def _async_update_data(self) -> dict:
        try:
            # --- Fetching and unpacking data dict ---
            data = self._fetch_and_prepare_data()

            temp: float = data["temperature"]
            humidity: float = data["humidity"]
            solar: float = data["solar"]
            wind_speed: float = data["wind"]
            raining: int = data["raining"]
            is_daytime: bool = data["is_daytime"]
            sunset: timedelta = data["sunset"]

            now = dt_util.now()
            self._track_sunset_conditions(
                sunset,
                now,
                temp,
                humidity,
            )

            # --- 1. Calculate Dew Point ---
            dew_point = calculate_dew_point(temp, humidity)

            dew_point_depression: float = 100.0

            if self.sunset_humi and self.sunset_temp:
                dew_point_sunset = calculate_dew_point(
                    self.sunset_temp, self.sunset_humi
                )
                # Temperature below dew point
                dew_point_depression = dew_point_sunset + DEW_TEMP_DIFFERENCE - temp

            # --- 2. Calculate Drying via Evaporation ---
            dry_rate = calculate_grass_drying(
                solar,
                humidity,
                temp,
                wind_speed,
            )

            # --- 3. Run the Model Logic ---
            current_moisture = self.moisture_level

            # A. Handle Rain (Resets everything)
            if raining == 1:
                current_moisture = 1.0

            # B. Handle Wetting (Dew at Night)
            elif (
                not is_daytime
                and current_moisture < DEW_MOIST_CAP
                and dew_point_depression > 0.0
            ):
                dew_rate = dew_point_depression * WETTING_INCREMENT
                moisture_increase = max(current_moisture, dew_rate)
                current_moisture = min(moisture_increase, DEW_MOIST_CAP)

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

    def _fetch_and_prepare_data(self) -> dict:
        # --- 1. Fetching ---
        temp_state = self.hass.states.get("sensor.outside_temperature")
        humidity_state = self.hass.states.get("sensor.tsensor_outside_humidity")
        solar_state = self.hass.states.get("sensor.solar_total_power")

        sun_state = self.hass.states.get("sun.sun")
        rain_state = self.hass.states.get("sensor.rain_sensor")
        weather_state = self.hass.states.get("weather.forecast_home_2")

        if not all(
            [
                temp_state,
                humidity_state,
                solar_state,
                sun_state,
                rain_state,
                weather_state,
            ]
        ):
            msg = "One or more required entities are missing."
            raise UpdateFailed(msg)

        try:
            # --- 2. Cleaning & Conversion ---

            data = {}

            data["temperature"] = self._get_float_state(temp_state, "temperature")
            data["humidity"] = self._get_float_state(humidity_state, "humidity")
            data["solar"] = self._get_float_state(solar_state, "solar")
            attributes_dict = weather_state.attributes
            data["wind"] = self._get_float_state(attributes_dict, "wind speed")

            try:
                data["raining"] = int(rain_state.state)
            except (ValueError, TypeError):
                msg = "Failed to convert raining state to int."
                raise UpdateFailed(msg) from None
            try:
                sunset_time_str = sun_state.attributes.get("next_setting")
                sunset_time = dt_util.parse_datetime(sunset_time_str)
                data["sunset"] = sunset_time
            except (ValueError, TypeError):
                msg = "Failed to parse sunset time."
                raise UpdateFailed(msg) from None
            if sun_state.state == "above_horizon":
                data["is_daytime"] = True
            else:
                data["is_daytime"] = False

        except Exception as e:
            msg = f"Error fetching data: {e}"
            raise UpdateFailed(msg) from e
        else:
            return data

    def _track_sunset_conditions(
        self,
        sunset: datetime,
        now: datetime,
        temp: float,
        humi: float,
    ) -> None:
        """Store the sunset temperature and humidity once per day."""
        trigger_time = sunset - timedelta(minutes=30)

        if (now >= trigger_time) and (not self.has_stored_sunset_values):
            self.sunset_temp = temp
            self.sunset_humi = humi
            self.has_stored_sunset_values = True

            LOGGER.info(
                "Moisture Tracker: Stored sunset values. Temp: %s, Humidity: %s",
                self.sunset_temp,
                self.sunset_humi,
            )

        # Reset the flag (In the 12:00-12:05 window)
        if now.hour == DEW_RESET_HOUR and now.minute < 5:  # noqa: PLR2004
            self.has_stored_sunset_values = False
            self.sunset_temp = None  # Clear old values
            self.sunset_humi = None
            LOGGER.info("Moisture Tracker: Reset daily sunset flag.")

    def _get_float_state(self, state_obj: State | None, name: str) -> float:
        """Convert a sensor's state attribute to a float."""
        if state_obj is None:
            msg = f"Required entity {name} could not be found (is None)."
            raise UpdateFailed(msg)

        if state_obj.state in ["unavailable", "unknown", "none"]:
            msg = f"State for {name} is unavailable or unknown ('{state_obj.state}')."
            raise UpdateFailed(msg)

        try:
            return float(state_obj.state)
        except (ValueError, TypeError) as err:
            msg = f"Failed to convert state for {name} ('{state_obj.state}') to float."
            raise UpdateFailed(msg) from err
