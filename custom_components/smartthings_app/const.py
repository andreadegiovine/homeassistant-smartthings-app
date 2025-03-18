DOMAIN = "smartthings_app"

# PLATFORMS = ["sensor", "number"]
PLATFORMS = ["sensor", "binary_sensor"]

FIELD_PERSONAL_TOKEN = "personal_token"

API_BASE_URL = "https://api.smartthings.com"
SCOPES = [
    "r:devices:*",
    "w:devices:*",
    "x:devices:*",
    "r:hubs:*",
    "r:locations:*",
    "w:locations:*",
    "x:locations:*",
    "r:scenes:*",
    "x:scenes:*",
    "r:rules:*",
    "w:rules:*",
    "r:installedapps",
    "w:installedapps"
]

AUTH_RETURN_URL_PATH = "/auth/smartthings"
AUTH_RETURN_URL_NAME = "auth:smartthings"