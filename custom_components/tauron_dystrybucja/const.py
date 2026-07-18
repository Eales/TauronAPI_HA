"""Constants for the Tauron Dystrybucja integration."""
from datetime import timedelta

DOMAIN = "tauron_dystrybucja"

API_BASE_URL = "https://www.tauron-dystrybucja.pl"
ENDPOINT_CITIES = "/waapi/enum/geo/cities"
ENDPOINT_STREETS = "/waapi/enum/geo/streets"
ENDPOINT_OUTAGES = "/waapi/outages/address"

CONF_CITY_NAME = "city_name"
CONF_CITY_GAID = "city_gaid"
CONF_STREET_NAME = "street_name"
CONF_STREET_GAID = "street_gaid"
CONF_HOUSE_NO = "house_no"
CONF_SCAN_INTERVAL = "scan_interval"

# How far ahead outages are fetched.
LOOKAHEAD = timedelta(days=30)

# Polling cadence, in minutes. Tauron publishes planned outages days in advance,
# so there is nothing to gain from polling aggressively. The floor keeps a
# misconfigured instance from hammering a free public API.
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 15
MAX_SCAN_INTERVAL = 1440

# Minimum length of a search phrase accepted by the Tauron API.
MIN_SEARCH_LENGTH = 3
