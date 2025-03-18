import voluptuous as vol
import logging
import secrets
from aiohttp import web_response
import time

from homeassistant import config_entries
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.helpers.network import get_url

from .smartthings import SmartThings
from .const import (
    DOMAIN,
    FIELD_PERSONAL_TOKEN,
    AUTH_RETURN_URL_PATH,
    AUTH_RETURN_URL_NAME
)

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
        self.data = {}
        self.smartthings = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            self.data.update(user_input)
            unique_id = res = secrets.token_hex(10)
            await self.async_set_unique_id(unique_id)
            return await self.async_step_create_app()

        errors = self.errors
        self.errors = {}

        if errors:
            await self.smartthings.delete_app()
            self.smartthings = None
            self.data = {}

        self.data.update({CONF_WEBHOOK_ID: secrets.token_hex(20)})

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_create_app(self, user_input=None):
        self.hass.http.register_view(ConfigFlowCallbackView)

        self.data.update({"redirect_uri": get_url(self.hass, prefer_external=True, prefer_cloud=True) + AUTH_RETURN_URL_PATH})

        try:
            self.smartthings = SmartThings(self.hass, None, self.data)
            self.smartthings.register_webhook()
            create_app_request = await self.smartthings.create_app()
        except Exception as e:
            self.errors[FIELD_PERSONAL_TOKEN] = str(e)
            return await self.async_step_user()

        self.data.update(create_app_request)
        self.smartthings._config.update(create_app_request)
        _LOGGER.error(self.data)

        return self.async_external_step(step_id="get_access_token", url=self.smartthings.get_oauth_url(self.flow_id))

    async def async_step_get_access_token(self, request=None):
        _LOGGER.error(request.query)
        if "error" in request.query:
            self.errors[FIELD_PERSONAL_TOKEN] = f"({request.query["error"]})"
            if "error_description" in request.query:
                self.errors[FIELD_PERSONAL_TOKEN] = self.errors[FIELD_PERSONAL_TOKEN] + f" {request.query["error_description"]}"
            return self.async_external_step_done(next_step_id="user")

        code = request.query["code"]

        try:
            access_token_request = await self.smartthings.get_access_token(code)
        except Exception as e:
            self.errors[FIELD_PERSONAL_TOKEN] = str(e)
            return await self.async_step_user()

        self.data.update({
            "access_token": access_token_request["access_token"],
            "refresh_token": access_token_request["refresh_token"],
            "expires_in": time.time() + int(access_token_request["expires_in"])
        })

        return self.async_external_step_done(next_step_id="finalize")


    async def async_step_finalize(self, user_input=None):
        if not "access_token" in self.data:
            self.errors[FIELD_PERSONAL_TOKEN] = "access_token_missing"
            return await self.async_step_user()

        return self.async_create_entry(title=(await self.smartthings.get_location_name()), data=self.data)


class ConfigFlowCallbackView(HomeAssistantView):
    """Handle callback from external auth."""

    url = AUTH_RETURN_URL_PATH
    name = AUTH_RETURN_URL_NAME
    requires_auth = False

    async def get(self, request):
        """Receive authorization confirmation."""
        hass = request.app[KEY_HASS]
        await hass.config_entries.flow.async_configure(
            flow_id=request.query["state"], user_input=request
        )

        return web_response.Response(
            headers={"content-type": "text/html"},
            text="<script>window.close()</script>Success! This window can be closed",
        )
