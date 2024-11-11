import aiohttp
import logging
from homeassistant import config_entries
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

_LOGGER = logging.getLogger(__name__)

# Poprawiony adres URL do Tauron API
API_BASE_URL = "https://www.tauron-dystrybucja.pl/waapi"

class TauronConfigFlow(config_entries.ConfigFlow, domain="tauron_dystrybucja"):
    """Handle a config flow for Tauron."""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def _fetch_cities(self, city_name):
        """Fetch city list from Tauron API asynchronously."""
        url = f"{API_BASE_URL}/enum/geo/cities?partName={city_name}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
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
            if len(city_name) < 3:
                errors["city"] = "too_short"
            else:
                cities = await self._fetch_cities(city_name)
                if cities:
                    city_suggestions = [city["Name"] for city in cities]
                    if city_name in city_suggestions:
                        selected_city = next((city for city in cities if city["Name"] == city_name), None)
                        if selected_city:
                            return self.async_create_entry(
                                title=selected_city["Name"],
                                data={"city": selected_city},
                            )
                else:
                    errors["city"] = "invalid_city"

        data_schema = vol.Schema({
            vol.Required("city"): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.SEARCH,
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
            if len(query) < 3:
                connection.send_result(msg["id"], [])
                return

            cities = await hass.async_add_executor_job(self._fetch_cities, query)
            suggestions = [city["Name"] for city in cities]
            connection.send_result(msg["id"], suggestions)

        websocket_api.async_register_command(hass, handle_city_suggestions)
