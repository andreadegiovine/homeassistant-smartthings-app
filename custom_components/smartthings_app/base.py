import logging
from datetime import ( datetime, UTC )
from dateutil.relativedelta import relativedelta
import re

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import ( CoordinatorEntity, DataUpdateCoordinator )
from homeassistant.helpers.event import ( async_track_state_change, async_track_point_in_time )
from homeassistant.components.sensor import ( RestoreSensor, SensorStateClass, SensorDeviceClass )
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt
from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import (
   DOMAIN
)
_LOGGER = logging.getLogger(__name__)

class SmartthingsCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, device, smartthings):
        super().__init__(hass, _LOGGER, name = DOMAIN)

        self._hass = hass
        self._device = device
        self._smartthings = smartthings
        self._device_components = {}
        self._device_entities = {}


    async def get_device_components(self):
        if self._device_components:
            return self._device_components

        request = await self._smartthings.get_device_status(self._device["deviceId"])
        device_components = request["components"]

        disabled_components = []
        if "main" in device_components and "custom.disabledComponents" in device_components["main"]:
            disabled_components = disabled_components + device_components["main"]["custom.disabledComponents"]["disabledComponents"]["value"]
            del device_components["main"]["custom.disabledComponents"]

        for component_name, component_data in device_components.items():
            if component_name in disabled_components:
                continue

            component_result = {}

            disabled_capabilities = [
                "ocf",
                "execute",
                "refresh",
                "samsungce.deviceIdentification",
                "samsungce.remoteManagementData",
                "samsungce.softwareUpdate",
                "samsungce.driverVersion",
                "samsungce.viewInside",
                "samsungce.quickControl",
                "samsungvd.thingStatus",
                "samsungvd.firmwareVersion",
                "samsungvd.deviceCategory",
                "samsungvd.supportsPowerOnByOcf",
                "sec.diagnosticsInformation",
                "custom.energyType"
            ]
            if "custom.disabledCapabilities" in component_data:
                disabled_capabilities = disabled_capabilities + component_data["custom.disabledCapabilities"]["disabledCapabilities"]["value"]
                del component_data["custom.disabledCapabilities"]
            if "samsungce.unavailableCapabilities" in component_data:
                disabled_capabilities = disabled_capabilities + component_data["samsungce.unavailableCapabilities"]["unavailableCommands"]["value"]
                del component_data["samsungce.unavailableCapabilities"]

            for capability_name, capability_data in component_data.items():
                capability_result = {}
                if capability_name in disabled_capabilities:
                    continue
                for item_name, item_data in capability_data.items():
                    if "value" in item_data and item_data["value"] in [None]:
                        continue
                    capability_result.update({item_name: item_data})
                component_result.update({capability_name: capability_result})

            if component_result:
                self._device_components.update({component_name: component_result})

        _LOGGER.error(self._device_components)
        return self._device_components


    def camel_to_snake(self, name):
        name = name.replace(".", "_")
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


    def camel_to_name(self, name):
        name = self.camel_to_snake(name)
        name = name.replace("_", " ")
        return name.title()


    async def get_device_entities(self, type):
        if self._device_entities:
            return self._device_entities.get(type, [])

        entities = {
            "switch": [],
            "sensor": [],
            "binary_sensor": []
        }
        components = await self.get_device_components()

        for module, items in components.items():
            for item_name, item_data in items.items():

                if item_name == "switch":
                    entities["switch"].append({
#                         "name": f"{module}-{self.camel_to_snake(item_name)}",
                        "name": self.camel_to_name(f"{module} {item_name}"),
                        "value": item_data["switch"]["value"] == "on",
                        "module": module,
                        "capability": item_name
                    })
                    continue

                if item_name == "samsungce.consumedEnergy":
                    value = 0
                    for months in item_data["monthlyUsage"]["value"]:
                        if months["month"] == datetime.now().strftime("%Y-%m"):
                            value = months["consumedEnergy"]
                    entities["sensor"].append({
                        "name": self.camel_to_name("monthlyUsage"),
                        "value": value,
                        "module": module,
                        "capability": item_name,
                        "property": "monthlyUsage",
                        "unit_of_measurement": "kWh"
                    })
                    continue

                if item_name == "powerConsumptionReport":
                    items = item_data["powerConsumption"]["value"]
                    entities["sensor"].append({
                        "name": self.camel_to_name("energy"),
                        "value": items["energy"],
                        "module": module,
                        "capability": item_name,
                        "property": "powerConsumption_energy",
                        "unit_of_measurement": "Wh"
                    })
                    entities["sensor"].append({
                        "name": self.camel_to_name("deltaEnergy"),
                        "value": items["deltaEnergy"],
                        "module": module,
                        "capability": item_name,
                        "property": "powerConsumption_deltaEnergy",
                        "unit_of_measurement": "Wh"
                    })
                    entities["sensor"].append({
                        "name": self.camel_to_name("power"),
                        "value": items["power"],
                        "module": module,
                        "capability": item_name,
                        "property": "powerConsumption_power",
                        "unit_of_measurement": "W"
                    })
                    entities["sensor"].append({
                        "name": self.camel_to_name("powerEnergy"),
                        "value": items["powerEnergy"],
                        "module": module,
                        "capability": item_name,
                        "property": "powerConsumption_powerEnergy",
                        "unit_of_measurement": "Wh"
                    })
                    entities["sensor"].append({
                        "name": self.camel_to_name("persistedEnergy"),
                        "value": items["persistedEnergy"],
                        "module": module,
                        "capability": item_name,
                        "property": "powerConsumption_persistedEnergy",
                        "unit_of_measurement": "Wh"
                    })
                    entities["sensor"].append({
                        "name": self.camel_to_name("energySaved"),
                        "value": items["energySaved"],
                        "module": module,
                        "capability": item_name,
                        "property": "powerConsumption_energySaved",
                        "unit_of_measurement": "Wh"
                    })
                    entities["sensor"].append({
                        "name": self.camel_to_name("persistedSavedEnergy"),
                        "value": items["persistedSavedEnergy"],
                        "module": module,
                        "capability": item_name,
                        "property": "powerConsumption_persistedSavedEnergy",
                        "unit_of_measurement": "Wh"
                    })
                    continue

                for sub_item_name, sub_item_data in item_data.items():

                    if isinstance(sub_item_data["value"], list) and len(sub_item_data["value"]) == 1:
                        sub_item_data["value"] = sub_item_data["value"][0]

                    if isinstance(sub_item_data["value"], bool) or (isinstance(sub_item_data["value"], str) and sub_item_data["value"] in ["on", "off", "open", "closed", "true", "false", "muted", "unmuted"]):
                        value = True
                        if isinstance(sub_item_data["value"], bool):
                            value = sub_item_data["value"]
                        elif sub_item_data["value"] in ["off",  "open", "true", "unmuted"]:
                            value = False

                        name = item_name

                        if len(item_name.split(".")) > 1:
                            name = item_name.split(".")[1]

                        if module != "main":
                            name = f"{module} {name}"

                        if isinstance(sub_item_data["value"], str) and not sub_item_name in ["contact", "mute", "remoteControlEnabled"]:
                            name = f"{name} {sub_item_name}"

                        name = name.replace("contactSensor", "Closed")

                        entities["binary_sensor"].append({
#                             "name": f"{module}-{self.camel_to_snake(item_name)}-{self.camel_to_snake(sub_item_name)}",
                            "name": self.camel_to_name(name),
                            "value": value,
                            "module": module,
                            "capability": item_name,
                            "property": sub_item_name
                        })
                    elif isinstance(sub_item_data["value"], list):
                        continue
                    elif isinstance(sub_item_data["value"], dict):
                        continue
                    else:
                        name = sub_item_name
                        if module != "main":
                            name = f"{module} {name}"
                        value = sub_item_data["value"]
                        if isinstance(sub_item_data["value"], str):
                            value = sub_item_data["value"].title()
                        data = {
#                             "name": f"{module}-{self.camel_to_snake(item_name)}-{self.camel_to_snake(sub_item_name)}",
                            "name": self.camel_to_name(name),
                            "value": str(value),
                            "module": module,
                            "capability": item_name,
                            "property": sub_item_name
                        }
                        if "unit" in sub_item_data:
                            data["unit_of_measurement"] = sub_item_data["unit"]
                        entities["sensor"].append(data)

        self._device_entities = entities
        return entities.get(type, [])



class SmartthingsBase(CoordinatorEntity):
    def __init__(self, coordinator: SmartthingsCoordinator, description):
        super().__init__(coordinator)
        # Component
        self._coordinator = coordinator
        self._device = coordinator._device
        self._smartthings = coordinator._smartthings
        # Core
        self.entity_description = description
        self._attr_unique_id = "smartthings_" + self._device["deviceId"] + "_" + description.key
#         self._attr_native_value = 0
        self._available = True
#         self._attr_state_class = SensorStateClass.TOTAL
#         self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_extra_state_attributes = {}
#         self._attr_suggested_display_precision = 2
        self._attr_translation_key = description.translation_key
        self._attr_has_entity_name = True

    @property
    def device_info(self):
        model = self._device["name"]
        sw_version = None
        if "ocf" in self._device:
            if "modelNumber" in self._device["ocf"]:
                model = f"{model} ({self._device["ocf"]["modelNumber"].split("|")[0]})"
            if "firmwareVersion" in self._device["ocf"]:
                sw_version = self._device["ocf"]["firmwareVersion"]
        return {
            "identifiers": {
                (DOMAIN, self._device["name"], "SmartThings App")
            },
            "name": self._device["label"],
            "model": model,
            "sw_version": sw_version,
            "manufacturer": self._device["manufacturerName"]
        }

class SmartthingsSensor(SmartthingsBase, RestoreSensor):
    def __init__(self, coordinator, description, default_value = None):
        super().__init__(coordinator, description)

        if default_value:
            self._attr_native_value = default_value

        if hasattr(description, "unit_of_measurement"):
            self._attr_native_unit_of_measurement = description.unit_of_measurement


class SmartthingsBinarySensor(SmartthingsBase, BinarySensorEntity):
    def __init__(self, coordinator, description, default_value):
        super().__init__(coordinator, description)

        self._attr_is_on = default_value