"""Constants for integration_blueprint."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "moisture_tracker"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"
PLATFORMS: list[str] = ["sensor"]
