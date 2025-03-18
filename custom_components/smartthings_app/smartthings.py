import logging
import aiohttp
import base64
import json
from copy import deepcopy
# import urllib.parse
import base64
import time

from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.components.webhook import DOMAIN as WEBHOOK_DOMAIN
from homeassistant.helpers.network import get_url
from homeassistant.components import webhook

from .base import SmartthingsCoordinator
from .const import (
    DOMAIN,
    FIELD_PERSONAL_TOKEN,
    API_BASE_URL,
    SCOPES
)

_LOGGER = logging.getLogger(__name__)

class SmartThings:
    def __init__(self, hass, entry = None, config = {}):
        self._hass = hass
        self._entry = entry
        self._config = config
#         self._data = {}
        self._session = aiohttp.ClientSession()
        self._coordinator_dict  = {}
        self._devices  = []

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
        data = self._config
        new_data = {}
        for key in data:
            new_data[key] = deepcopy(data[key])
        if name not in new_data:
            new_data[name] = None
        new_data[name] = value
        self._hass.config_entries.async_update_entry(self._entry, data=new_data)
        self._hass.config_entries._async_schedule_save()
        self._config = new_data


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
        return {
            "Authorization": f"Bearer {self.personal_token}"
        }

    @property
    def headers_basic_auth(self):
        if not self.get_config("client_id") or not self.get_config("client_secret"):
            return False
        basic_auth = base64.b64encode(bytes(self.get_config("client_id") + ":" + self.get_config("client_secret"), 'utf-8')).decode('utf-8')
        return {
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

    @property
    def headers_baerer_auth(self):
        if not self.get_config("access_token") or not self.get_config("access_token"):
            return False
        return {
            "Authorization": f"Bearer {self.get_config("access_token")}"
        }


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
        if "lifecycle" in body:
#             if body["lifecycle"] == "CONFIRMATION":
#                 if "confirmationData" in body and "confirmationUrl" in body["confirmationData"]:
#                     self._data.update({"confirmationUrl": body["confirmationData"]["confirmationUrl"]})
#                     return None
            if body["lifecycle"] == "PING":
                return json.dumps({"pingData": body["pingData"]})
        return await request.text()


    def register_webhook(self):
        if not self.webhook_id:
            return False
        if not self.webhook_id in self._hass.data.setdefault(WEBHOOK_DOMAIN, {}):
            webhook.async_register(self._hass, DOMAIN, "SmartThings App", self.webhook_id, self._handle_webhook)


    async def create_app(self):
        if not self.webhook_url or not self.personal_token:
            return False

#         url =  f"{API_BASE_URL}/apps?requireConfirmation=true&signatureType=APP_RSA"
        url =  f"{API_BASE_URL}/apps"
        name = f"Home Assistant for {self.hass_url}"
        payload = {
            "appName": f"hass.{self.webhook_id}",
            "appType": "API_ONLY",
#             "appType": "WEBHOOK_SMART_APP",
            "classifications": ["CONNECTED_SERVICE"],
#             "classifications": ["AUTOMATION"],
            "displayName": name,
            "description": name,
            "singleInstance": True,
            "oauth": {
                "clientName": "Hass",
                "scope": SCOPES,
                "redirectUris": [self.get_config("redirect_uri")]
            },
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

#         if "confirmationUrl" in self._data:
#             await self.make_http_request(self._data["confirmationUrl"])
        return {"app_id": request["app"]["appId"], "client_id": request["oauthClientId"], "client_secret": request["oauthClientSecret"]}


#     async def update_app(self):
#         if not self.get_config("app_id"):
#             return False
#         url =  f"{API_BASE_URL}/apps/{self.get_config("app_id")}"
#         name = f"Home Assistant for {self.hass_url}"
#         payload = {
#             "appType": "WEBHOOK_SMART_APP",
#             "classifications": ["CONNECTED_SERVICE"],
#             "displayName": name,
#             "description": name,
#             "webhookSmartApp": {
#               "targetUrl": self.webhook_url
#             }
#         }
#         request = await self.make_http_request(url, 'PUT', self.headers_personal_token, None, payload)


    async def delete_app(self):
        if not self.get_config("app_id"):
            return False
        url =  f"{API_BASE_URL}/apps/{self.get_config("app_id")}"
        request = await self.make_http_request(url, 'DELETE', self.headers_personal_token)


    async def get_location_name(self):
        url =  f"{API_BASE_URL}/locations"
        request = await self.make_http_request(url, 'GET', self.headers_personal_token)
        if not "items" in request or not request["items"] or not "name" in request["items"][0]:
            return False
        return request["items"][0]["name"]


    def get_oauth_url(self, flow_id):
        client_id = self.get_config("client_id")
        scopes = "+".join(SCOPES)
        return  f"{API_BASE_URL}/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri={self.get_config("redirect_uri")}&state={flow_id}&scope={scopes}"


    async def get_access_token(self, code):
        url =  f"{API_BASE_URL}/oauth/token"
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.get_config("client_id"),
            "code": code,
            "redirect_uri": self.get_config("redirect_uri")
        }
        return await self.make_http_request(url, 'POST', self.headers_basic_auth, None, None, payload)


    async def get_refresh_token(self):
        if time.time() < (self.get_config("expires_in") - 10):
            return

        url =  f"{API_BASE_URL}/oauth/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.get_config("client_id"),
            "refresh_token": self.get_config("refresh_token"),
            "redirect_uri": self.get_config("redirect_uri")
        }
        refresh_token_request = await self.make_http_request(url, 'POST', self.headers_basic_auth, None, None, payload)
        self.save_config("access_token", refresh_token_request["access_token"])
        self.save_config("refresh_token", refresh_token_request["refresh_token"])
        self.save_config("expires_in", time.time() + int(refresh_token_request["expires_in"]))


    async def get_devices(self):
        await self.get_refresh_token()

        if self._devices:
            return self._devices

        url =  f"{API_BASE_URL}/v1/devices"
        request = await self.make_http_request(url, 'GET', self.headers_baerer_auth)
        if not "items" in request:
            return []
        self._devices = request["items"]
        return self._devices


    async def get_device_status(self, device_id):
        await self.get_refresh_token()
        url =  f"{API_BASE_URL}/v1/devices/{device_id}/status"
        return await self.make_http_request(url, 'GET', self.headers_baerer_auth)


    async def async_get_coordinator_by_device_id(self, device_id):
        if device_id in self._device_dict:
            return self._device_dict[device_id]
        return None


    async def async_get_coordinator(self, device):
        device_id = device["deviceId"]
        if device_id in self._coordinator_dict:
            return self._coordinator_dict[device_id]
        coordinator = SmartthingsCoordinator(self._hass, device, self)
        self._coordinator_dict[device_id] = coordinator
        return coordinator