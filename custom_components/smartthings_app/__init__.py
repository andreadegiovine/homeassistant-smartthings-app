import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .smartthings import SmartThings
from .const import (
   DOMAIN,
   PLATFORMS
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry):

    smartthings = SmartThings(hass, config)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config.entry_id] = smartthings

    devices = {}

    try:
        devices = await smartthings.get_devices()
#     except ConfigEntryAuthFailed as e:
#         raise ConfigEntryAuthFailed from e
    except Exception as e:
        _LOGGER.error(str(e))
#         await stellantis.close_session()
        devices = {}

    for device in devices:
        coordinator = await smartthings.async_get_coordinator(device)
#         await coordinator.async_config_entry_first_refresh()

    if devices:
        await hass.config_entries.async_forward_entry_setups(config, PLATFORMS)

    return True
