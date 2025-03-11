import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

# from .base import EnergyCostCoordinator
# from .const import (
#                        DOMAIN,
#                        PLATFORMS
#                    )

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry):

#     coordinator = EnergyCostCoordinator(hass, config)
#     hass.data.setdefault(DOMAIN, {})[config.entry_id] = coordinator
#
#     await hass.config_entries.async_forward_entry_setups(config, PLATFORMS)

    # Return boolean to indicate that initialization was successful.
    return True
