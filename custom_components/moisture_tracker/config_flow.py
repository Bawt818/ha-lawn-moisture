"""Config flow for moisture_tracker."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

if TYPE_CHECKING:
    from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_HUMI_SENSOR,
    CONF_RAIN_SENSOR,
    CONF_SOLAR_SENSOR,
    CONF_SUN_SENSOR,
    CONF_TEMP_SENSOR,
    CONF_WEATHER_ENTITY,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema({})


class MoistureTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Moisture Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # --- 1. Check if it's already set up ---
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        # --- 2. Handle the user submitting the form ---
        if user_input is not None:
            return self.async_create_entry(title="Grass Moisture", data=user_input)

        # Define the form schema with Selectors
        data_schema = vol.Schema(
            {
                vol.Required(CONF_TEMP_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="temperature"
                    )
                ),
                vol.Required(CONF_HUMI_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="humidity"
                    )
                ),
                vol.Required(CONF_SOLAR_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="power")
                ),
                vol.Required(CONF_RAIN_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "binary_sensor"])
                ),
                vol.Required(CONF_WEATHER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
                # Optional: You can set a default for sun.sun
                vol.Optional(
                    CONF_SUN_SENSOR, default="sun.sun"
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sun")),
            }
        )

        # --- 3. Show the form to the user ---
        return self.async_show_form(step_id="user", data_schema=data_schema)
