import aiohttp
import logging
import urllib.parse
from homeassistant import config_entries
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

# Ustawienie logowania na poziomie DEBUG
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://www.tauron-dystrybucja.pl/waapi"

class TauronConfigFlow(config_entries.ConfigFlow, domain="tauron_dystrybucja"):
    """Handle a config flow for Tauron."""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def _fetch_cities(self, city_name):
        """Fetch city list from Tauron API asynchronously."""
        _LOGGER.debug(f"_fetch_cities called with city_name: {city_name}")
        if not city_name or len(city_name.strip()) < 3:
            _LOGGER.debug("City name too short, skipping API request.")
            return []

        try:
            encoded_city_name = urllib.parse.quote_plus(city_name)
            url = f"{API_BASE_URL}/enum/geo/cities?partName={encoded_city_name}"
            headers = {
                "User-Agent": "HomeAssistant",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            _LOGGER.debug(f"Sending request to URL: {url} with headers: {headers}")

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    _LOGGER.debug(f"Request URL: {url}, Status: {response.status}")
                    if response.status == 400:
                        _LOGGER.error("Received 400 Bad Request from API. Please check the query parameters.")
                        return []
                    response.raise_for_status()
                    response_text = await response.text()
                    _LOGGER.debug(f"Response text: {response_text}")
                    data = await response.json()
                    _LOGGER.debug(f"Fetched cities data: {data}")
                    return data
        except aiohttp.ClientError as ce:
            _LOGGER.error(f"ClientError occurred: {ce}")
            return []
        except Exception as e:
            _LOGGER.error(f"Unexpected error occurred while fetching cities: {e}")
            return []

    async def async_step_user(self, user_input=None):
        """Handle the initial step of configuring the integration with dynamic suggestions."""

        _LOGGER.debug("async_step_user called")
        errors = {}

        if user_input is not None:
            city_name = user_input.get("city")
            if not city_name or len(city_name.strip()) == 0:
                _LOGGER.warning("City name cannot be empty.")
                errors["city"] = "empty_city"
            elif len(city_name) < 3:
                _LOGGER.warning("City name too short, must be at least 3 characters.")
                errors["city"] = "too_short"
            else:
                _LOGGER.debug("Fetching cities from _fetch_cities method.")
                cities = await self._fetch_cities(city_name)
                _LOGGER.debug("Checking if any cities were found.")
                if cities:
                    city_suggestions = [city["Name"] for city in cities]
                    _LOGGER.debug(f"City suggestions: {city_suggestions}")
                    selected_city = next((city for city in cities if city["Name"].lower() == city_name.lower()), None)
                    if selected_city:
                        _LOGGER.debug(f"Selected city: {selected_city}")
                        return self.async_create_entry(
                            title=selected_city["Name"],
                            data={
                                "city_name": selected_city["Name"],
                                "gus": selected_city["GUS"],
                                "district": selected_city["DistrictName"],
                                "province": selected_city["ProvinceName"],
                                "gaid": selected_city["GAID"]
                            },
                        )
                    else:
                        _LOGGER.warning("No city matched exactly, please check the input.")
                        errors["city"] = "no_match"
                else:
                    _LOGGER.warning("No valid cities found for the given input.")
                    errors["city"] = "invalid_city"

        data_schema = vol.Schema({
            vol.Required("city"): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                    placeholder="Wpisz nazwę miasta (minimum 3 znaki)",
                    autocomplete=True
                )
            )
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_register_websockets(hass):
        """Register websockets for fetching dynamic city data."""
        _LOGGER.debug("Registering websockets for city suggestions")
        @websocket_api.websocket_command({
            vol.Required("type"): "tauron_dystrybucja/city_suggestions",
            vol.Required("query"): cv.string,
        })
        @callback
        async def handle_city_suggestions(hass, connection, msg):
            """Handle city suggestions dynamically via websocket."""
            query = msg.get("query")
            _LOGGER.debug(f"WebSocket received query: {query}")
            if not query or len(query.strip()) < 3:
                _LOGGER.warning("Query too short for suggestions, must be at least 3 characters.")
                connection.send_result(msg["id"], [])
                return

            flow = hass.data.get("tauron_dystrybucja")
            if not flow:
                _LOGGER.error("Flow data not found in hass, unable to fetch city suggestions.")
                connection.send_result(msg["id"], [])
                return

            try:
                _LOGGER.debug(f"Attempting to fetch cities for query: {query}")
                cities = await flow._fetch_cities(query)
                if cities:
                    suggestions = [city["Name"] for city in cities]
                else:
                    suggestions = []
                _LOGGER.debug(f"WebSocket suggestions: {suggestions}")
                connection.send_result(msg["id"], suggestions)
            except Exception as e:
                _LOGGER.error(f"Error in WebSocket suggestion handling: {e}")
                connection.send_result(msg["id"], [])

        websocket_api.async_register_command(hass, handle_city_suggestions)
