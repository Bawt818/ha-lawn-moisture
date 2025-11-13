"""Sensor platform for integration_blueprint."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MoistureDataUpdateCoordinator

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="integration_blueprint",
        name="Integration Sensor",
        icon="mdi:format-quote-close",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: MoistureDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        GrassMoistureSensor(coordinator),
        DewPointSensor(coordinator),
    ])


class GrassMoistureSensor(
    CoordinatorEntity[MoistureDataUpdateCoordinator],SensorEntity
    ):
    """
    The main sensor for grass moisture.

    It inherits from CoordinatorEntity to auto-link with the coordinator.
    """

    # --- Properties for HA UI ---
    _attr_name = "Grass Moisture"
    _attr_device_class = SensorDeviceClass.MOISTURE
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: MoistureDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        # Pass the coordinator to the parent class
        super().__init__(coordinator)

        # Set a unique ID for this entity
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_grass_moisture"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data["moisture"] * 100.0
        return None

    '''
    def __init__(
        self,
        coordinator: BlueprintDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description

    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("body")
    '''
class DewPointSensor(CoordinatorEntity[MoistureDataUpdateCoordinator], SensorEntity):
    """A sensor to expose the calculated dew point."""

    _attr_name = "Calculated Dew Point"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: MoistureDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_dew_point"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            # Get the 'dew_point' value from the same data dict
            return self.coordinator.data["dew_point"]
        return None
