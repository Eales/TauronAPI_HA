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

    async def _fetch_streets(self, street_name, owner_gaid):
        """Fetch street list from Tauron API asynchronously."""
        url = f"{API_BASE_URL}/enum/geo/streets?partName={street_name}&ownerGAID={owner_gaid}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    _LOGGER.debug(f"Fetched streets data: {data}")  # Logowanie odpowiedzi
                    return data
            except Exception as e:
                _LOGGER.error(f"Error fetching streets: {e}")
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
                            return await self.async_step_street(selected_city)
                else:
                    errors["city"] = "invalid_city"

        data_schema = vol.Schema({
            vol.Required("city"): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.SEARCH,
                    autocomplete=lambda value: [city["Name"] for city in await self._fetch_cities(value) if len(value) >= 3]
                )
            )
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"city": "Wpisz nazwę miasta (minimum 3 znaki) i wybierz z sugerowanych opcji."}
        )

    async def async_step_street(self, city_data):
        """Handle the step of selecting the street with dynamic suggestions."""
        errors = {}

        if self.context.get("user_input") is not None:
            street_name = self.context["user_input"].get("street")
            if len(street_name) < 3:
                errors["street"] = "too_short"
            else:
                streets = await self._fetch_streets(street_name, city_data["GAID"])
                if streets:
                    street_suggestions = [street["FullName"] for street in streets]
                    if street_name in street_suggestions:
                        selected_street = next((street for street in streets if street["FullName"] == street_name), None)
                        if selected_street:
                            return self.async_create_entry(
                                title=f"{city_data['Name']}, {selected_street['FullName']}",
                                data={"city": city_data, "street": selected_street},
                            )
                else:
                    errors["street"] = "invalid_street"

        data_schema = vol.Schema({
            vol.Required("street"): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.SEARCH,
                    autocomplete=lambda value: [street["FullName"] for street in await self._fetch_streets(value, city_data["GAID"]) if len(value) >= 3]
                )
            )
        })

        return self.async_show_form(
            step_id="street",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"street": "Wpisz nazwę ulicy (minimum 3 znaki) i wybierz z sugerowanych opcji."}
        )

    @staticmethod
    @callback
    def async_register_websockets(hass):
        """Register websockets for fetching dynamic city and street data."""
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

        @websocket_api.websocket_command({
            vol.Required("type"): "tauron/street_suggestions",
            vol.Required("query"): cv.string,
            vol.Required("owner_gaid"): cv.positive_int,
        })
        @callback
        async def handle_street_suggestions(hass, connection, msg):
            """Handle street suggestions dynamically via websocket."""
            query = msg.get("query")
            owner_gaid = msg.get("owner_gaid")
            if len(query) < 3:
                connection.send_result(msg["id"], [])
                return

            streets = await hass.async_add_executor_job(self._fetch_streets, query, owner_gaid)
            suggestions = [street["FullName"] for street in streets]
            connection.send_result(msg["id"], suggestions)

        websocket_api.async_register_command(hass, handle_city_suggestions)
        websocket_api.async_register_command(hass, handle_street_suggestions)
