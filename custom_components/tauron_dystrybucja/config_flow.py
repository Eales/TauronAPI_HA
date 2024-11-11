import aiohttp
import logging
from homeassistant import config_entries
import voluptuous as vol

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
        """Handle the initial step of configuring the integration in a single step."""
        errors = {}
        city_choices = {}

        if user_input is not None:
            # Sprawdzamy miasto, które użytkownik wpisał
            city_name = user_input["city"]
            if len(city_name) < 3:
                errors["city"] = "too_short"
            else:
                cities = await self._fetch_cities(city_name)
                if cities:
                    city_choices = {city["Name"]: city["Name"] for city in cities}
                    if user_input.get("selected_city") in city_choices:
                        selected_city_name = user_input["selected_city"]
                        city_data = next((city for city in cities if city["Name"] == selected_city_name), None)
                        if city_data:
                            # Zapisz dane miasta
                            return self.async_create_entry(
                                title=city_data["Name"],
                                data=city_data,
                            )
                else:
                    errors["city"] = "invalid_city"

        data_schema = vol.Schema({
            vol.Required("city"): str
        })

        if city_choices:
            data_schema = data_schema.extend({
                vol.Required("selected_city"): vol.In(city_choices)
            })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
