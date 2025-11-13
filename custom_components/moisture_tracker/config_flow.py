"""Config flow for moisture_tracker."""

from __future__ import annotations

import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant

from .const import DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema({}) 

class MoistureTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Moisture Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        
        # --- 1. Check if it's already set up ---
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        # --- 2. Handle the user submitting the form ---
        if user_input is not None:
            return self.async_create_entry(title="Grass Moisture", data={})

        # --- 3. Show the form to the user ---
        return self.async_show_form(
            step_id="user", 
            data_schema=STEP_USER_DATA_SCHEMA
        )