import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.const import (UnitOfTemperature, UnitOfEnergy, UnitOfPower)
from homeassistant.components.sensor.const import SensorDeviceClass

from .base import SmartthingsSensor
from .const import (
   DOMAIN
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities):
    smartthings = hass.data[DOMAIN][config.entry_id]

    entities = []

    devices = await smartthings.get_devices()

    unit_map = {
        "C": {
            "unit_of_measurement": UnitOfTemperature.CELSIUS,
            "icon": "mdi:thermometer",
            "device_class" : SensorDeviceClass.TEMPERATURE
        },
        "kWh": {
            "unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
            "icon": "mdi:lightning-bolt",
            "device_class" : SensorDeviceClass.ENERGY,
            "suggested_display_precision": 2
        },
        "Wh": {
            "unit_of_measurement": UnitOfEnergy.WATT_HOUR,
            "icon": "mdi:lightning-bolt",
            "device_class" : SensorDeviceClass.ENERGY,
            "suggested_display_precision": 2
        },
        "W": {
            "unit_of_measurement": UnitOfPower.WATT,
            "icon": "mdi:lightning-bolt",
            "device_class" : SensorDeviceClass.ENERGY,
            "suggested_display_precision": 2
        }
    }

    for device in devices:
        coordinator = await smartthings.async_get_coordinator(device)
        sensors = await coordinator.get_device_entities("sensor")
        _LOGGER.error(sensors)
        for sensor in sensors:
            default_config = unit_map.get(sensor.get("unit_of_measurement", None), {})
            description = SensorEntityDescription(
                key = sensor["name"],
                name = sensor["name"],
                translation_key = sensor["name"],
                unit_of_measurement = default_config.get("unit_of_measurement", None),
                icon = default_config.get("icon", None),
                device_class = default_config.get("device_class", None),
                suggested_display_precision = default_config.get("suggested_display_precision", None)
            )
            entities.extend([SmartthingsSensor(coordinator, description, sensor["value"])])

    async_add_entities(entities)