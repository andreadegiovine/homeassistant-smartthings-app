import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.binary_sensor import BinarySensorEntityDescription

from .base import SmartthingsBinarySensor
from .const import (
   DOMAIN
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities):
    smartthings = hass.data[DOMAIN][config.entry_id]

    entities = []

    devices = await smartthings.get_devices()

    for device in devices:
        coordinator = await smartthings.async_get_coordinator(device)
        sensors = await coordinator.get_device_entities("binary_sensor")
        _LOGGER.error(sensors)
        for sensor in sensors:
            description = BinarySensorEntityDescription(
                key = sensor["name"],
                name = sensor["name"],
                translation_key = sensor["name"]
            )
            entities.extend([SmartthingsBinarySensor(coordinator, description, sensor["value"])])

    async_add_entities(entities)