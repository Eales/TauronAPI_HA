import aiohttp
import logging
from homeassistant import config_entries
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

# Ustawienie logowania na poziomie DEBUG
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

# Poprawiony adres URL do Tauron API
API_BASE_URL = "https://www.tauron-dystrybucja.pl/waapi"

class TauronConfigFlow(config_entries.ConfigFlow, domain="tauron_dystrybucja"):
    """Handle a config flow for Tauron."""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def _fetch_cities(self, city_name):
        """Fetch city list from Tauron API asynchronously."""
        if len(city_name) < 3:
            _LOGGER.debug("City name too short, skipping API request.")
            return []

        url = f"{API_BASE_URL}/enum/geo/cities?partName={city_name}"
        _LOGGER.debug(f"Fetching cities with partName: {city_name}")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    _LOGGER.debug(f"Request URL: {url}, Status: {response.status}")
                    response.raise_for_status()
                    data = await response.json()
                    _LOGGER.debug(f"Fetched cities data: {data}")  # Logowanie odpowiedzi
                    return data
            except Exception as e:
                _LOGGER.error(f"Error fetching cities: {e}")
                return []

    async def async_step_user(self, user_input=None):
        """Handle the initial step of configuring the integration with dynamic suggestions."""
        errors = {}

        if user_input is not None:
            city_name = user_input.get("city")
            _LOGGER.debug(f"User input for city: {city_name}")
            if len(city_name) < 3:
                _LOGGER.warning("City name too short, must be at least 3 characters.")
                errors["city"] = "too_short"
            else:
                cities = await self._fetch_cities(city_name)
                if cities:
                    city_suggestions = [city["Name"] for city in cities]
                    _LOGGER.debug(f"City suggestions: {city_suggestions}")
                    selected_city = next((city for city in cities if city["Name"] == city_name), None)
                    if selected_city:
                        _LOGGER.debug(f"Selected city: {selected_city}")
                        # Zapisujemy pełne dane miasta, w tym GUS
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
                    _LOGGER.warning("No valid cities found for the given input.")
                    errors["city"] = "invalid_city"

        # W przypadku gdy user_input jest None (czyli początkowe wyświetlenie formularza)
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
        @websocket_api.websocket_command({
            vol.Required("type"): "tauron/city_suggestions",
            vol.Required("query"): cv.string,
        })
        @callback
        async def handle_city_suggestions(hass, connection, msg):
            """Handle city suggestions dynamically via websocket."""
            query = msg.get("query")
            _LOGGER.debug(f"WebSocket received query: {query}")
            if len(query) < 3:
                _LOGGER.warning("Query too short for suggestions, must be at least 3 characters.")
                connection.send_result(msg["id"], [])
                return

            try:
                flow = hass.config_entries.flow.async_get_handler("tauron_dystrybucja")
                cities = hass.async_run_job(flow._fetch_cities, query)
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
