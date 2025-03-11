import logging
import aiohttp
import base64
import json
from copy import deepcopy

from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.components.webhook import DOMAIN as WEBHOOK_DOMAIN
from homeassistant.helpers.network import get_url
from homeassistant.components import webhook

from .const import (
    DOMAIN,
    FIELD_PERSONAL_TOKEN,
    API_BASE_URL
)

_LOGGER = logging.getLogger(__name__)

class SmartThings:
    def __init__(self, hass, entry = None, config = {}):
        self._hass = hass
        self._entry = entry
        self._config = config
        self._session = aiohttp.ClientSession()

        if self._entry:
            self._config = self._entry.data

        _LOGGER.error(self._config)



    async def close_session(self):
        await self._session.close()


    def get_config(self, name):
        if name in self._config:
            return self._config[name]
        return None


    def save_config(self, name, value):
        data = self._entry.data
        new_data = {}
        for key in data:
            new_data[key] = deepcopy(data[key])
        if name not in new_data:
            new_data[name] = None
        new_data[name] = value
        self._hass.config_entries.async_update_entry(self._entry, data=new_data)
        self._hass.config_entries._async_schedule_save()


    @property
    def hass_url(self):
        return get_url(self._hass, prefer_external=True, prefer_cloud=True)

    @property
    def webhook_id(self):
        webhook_id = self.get_config(CONF_WEBHOOK_ID)
        if not webhook_id:
            return False
        return webhook_id

    @property
    def webhook_url(self):
        if not self.webhook_id:
            return False
        return self.hass_url + "/api/webhook/" + self.webhook_id

    @property
    def personal_token(self):
        personal_token = self.get_config(FIELD_PERSONAL_TOKEN)
        if not personal_token:
            return False
        return personal_token

    @property
    def headers_personal_token(self):
        if not self.personal_token:
            return False
        return {"Authorization": f"Bearer {self.personal_token}"}


    async def make_http_request(self, url, method = 'GET', headers = None, params = None, json = None, data = None):
        _LOGGER.debug("---------- START make_http_request")
        _LOGGER.debug(url)
        _LOGGER.debug(method)
        _LOGGER.debug(headers)
        _LOGGER.debug(params)
        _LOGGER.debug(json)
        _LOGGER.debug(data)
        result = {}
        error = None
        async with self._session.request(method, url, params=params, json=json, data=data, headers=headers) as resp:
            if method != "DELETE" and (await resp.text()):
                result = await resp.json()
            if not str(resp.status).startswith("20"):
                _LOGGER.error(f"{method} request error {str(resp.status)}: {resp.url}")

                if "error" in result and "code" in result["error"] and "message" in result["error"]:
                    error = f"({result["error"]["code"]}) {result["error"]["message"]}"

                    if "details" in result["error"]:
                        for detail in result["error"]["details"]:
                            error = error + f" - ({detail["code"]}) {detail["message"]}."

        _LOGGER.debug(result)
        _LOGGER.debug("---------- END make_http_request")

#             if str(resp.status) == "400" and "error" in result and result["error"] == "invalid_grant":
#                 # Token expiration
#                 raise ConfigEntryAuthFailed(error)
        if error:
            # Generic error
            raise Exception(error)
        return result


    async def _handle_webhook(self, hass, webhook_id, request):
        _LOGGER.debug("---------- START _handle_webhook")
        body = await request.json()
        _LOGGER.debug(body)
        return await request.text()


    def register_webhook(self):
        if not self.webhook_id:
            return False
        if not self.webhook_id in self._hass.data.setdefault(WEBHOOK_DOMAIN, {}):
            webhook.async_register(self._hass, DOMAIN, "SmartThings App", self.webhook_id, self._handle_webhook)


    async def get_credentials(self):
        if not self.personal_token:
            return False
        app = await self.get_app()
        if not app:
            return False
        return await self.get_app_credentials(app["appId"])


    async def get_app(self):
        if not self.webhook_url:
            return False

        apps = await self.get_apps()
        for app in apps:
            app_data = await self.get_app_data(app["appId"])
            if "webhookSmartApp" in app_data and "targetUrl" in app_data["webhookSmartApp"] and app_data["webhookSmartApp"]["targetUrl"] == self.webhook_url:
                return app_data

        url =  f"{API_BASE_URL}/apps"
        payload = {
            "appName": f"hass.{self.webhook_id}",
            "appType": "WEBHOOK_SMART_APP",
            "classifications": ["CONNECTED_SERVICE"],
            "displayName": "Home Assistant",
            "description": f"Home Assistant for {self.hass_url}",
            "singleInstance": True,
            "ui": {
              "dashboardCardsEnabled": False,
              "preInstallDashboardCardsEnabled": False
            },
            "webhookSmartApp": {
              "targetUrl": self.webhook_url
            }
        }
        request = await self.make_http_request(url, 'POST', self.headers_personal_token, None, payload)
        if not "app" in request:
            return False
        return request["app"]


    async def get_apps(self):
        url =  f"{API_BASE_URL}/apps"
        request = await self.make_http_request(url, 'GET', self.headers_personal_token)
        if not "items" in request:
            return False
        return request["items"]


    async def get_app_data(self, app_id):
        url =  f"{API_BASE_URL}/apps/{app_id}"
        request = await self.make_http_request(url, 'GET', self.headers_personal_token)
        return request


    async def get_app_credentials(self, app_id):
        url =  f"{API_BASE_URL}/apps/{app_id}/oauth/generate"
        payload = {
            "clientName": "Home Assistant",
            "scope": ["r:devices:$", "r:devices:*"]
        }
        request = await self.make_http_request(url, 'POST', self.headers_personal_token, None, payload)
        if not "oauthClientId" in request or not "oauthClientSecret" in request:
            return False
        return {"client_id": request["oauthClientId"], "client_secret": request["oauthClientSecret"]}


    def get_oauth_url(self):
        client_id = self.get_config("client_id")
        scopes = "r:devices:* w:devices:* x:devices:* r:hubs:* r:locations:* w:locations:* x:locations:* r:scenes:* x:scenes:* r:rules:* w:rules:* sse r:installedapps w:installedapps"
        redirect = "https://test.it"
        return  f"{API_BASE_URL}/oauth/authorize?client_id={client_id}&response_type=code&scope={scopes}&redirect_uri={redirect}"
