import voluptuous as vol
import logging
import secrets

from homeassistant import config_entries
from homeassistant.const import CONF_WEBHOOK_ID

from .const import ( DOMAIN, FIELD_PERSONAL_TOKEN )
from .smartthings import SmartThings

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(FIELD_PERSONAL_TOKEN): str,
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""
    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self.errors = {}
        self.data = {
            CONF_WEBHOOK_ID: secrets.token_hex(16)
        }
        self.smartthings = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        if user_input is not None:
            self.data.update(user_input)
            unique_id = res = secrets.token_hex(10)
            await self.async_set_unique_id(unique_id)
            return await self.async_step_get_credentials()

        errors = self.errors
        self.errors = {}

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_get_credentials(self, user_input=None):
        try:
            self.smartthings = SmartThings(self.hass, None, self.data)
            self.smartthings.register_webhook()
            credentials = await self.smartthings.get_credentials()
            self.data.update(credentials)
        except Exception as e:
            self.errors[FIELD_PERSONAL_TOKEN] = str(e)
            return await self.async_step_user()

        self.smartthings._config.update(credentials)

        return self.async_external_step(step_id="get_access_token", url=self.smartthings.get_oauth_url())


    async def async_step_get_access_token(self, request=None):
        _LOGGER.error(request)

#     async def async_step_final(self, user_input=None):
#         """Handle the final step."""
#
#         step_schema = DATA_SCHEMA_2
#
#         if user_input is not None:
#             if user_input[FIELD_FIXED_FEE] is not None:
#                 config_data = dict()
#                 config_data.update(self.data)
#                 config_data.update(user_input)
#                 _LOGGER.info(config_data)
#                 return self.async_create_entry(title=config_data[FIELD_NAME], data=config_data)
#
#         if self.data[FIELD_PUN_MODE]:
#             step_schema = step_schema.extend({
#                 vol.Required(FIELD_PUN_ENTITY): selector({ "entity": { "integration": "pun_sensor", "domain": "sensor" } })
#             })
#
#         if self.data[FIELD_RATE_MODE] == FIELD_RATE_MODE_MONO:
#             step_schema = step_schema.extend({
#                 vol.Required(FIELD_MONO_RATE, default=0.01328): vol.Coerce(float)
#             })
#         else:
#             step_schema = step_schema.extend({
#                 vol.Required(FIELD_CURRENT_RATE_ENTITY): selector({ "entity": { "device_class": "enum", "integration": "pun_sensor", "domain": "sensor" } }),
#                 vol.Required(FIELD_F1_RATE, default=0.01328): vol.Coerce(float),
#                 vol.Required(FIELD_F2_RATE, default=0.01328): vol.Coerce(float),
#                 vol.Required(FIELD_F3_RATE, default=0.01328): vol.Coerce(float),
#             })
#
#         return self.async_show_form(
#             step_id="final", data_schema=step_schema
#         )
