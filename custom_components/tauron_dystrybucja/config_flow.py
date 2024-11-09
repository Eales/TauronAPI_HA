import aiohttp
import logging
from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://api.tauron.pl"  # Zaktualizuj ten URL do odpowiedniego

class TauronConfigFlow(config_entries.ConfigFlow, domain="tauron"):
    """Handle a config flow for Tauron."""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def _fetch_cities(self, city_name):
        """Fetch city list from Tauron API asynchronously."""
        url = f"{API_BASE_URL}/waapi/enum/geo/cities?partName={city_name}"
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
        """Handle the initial step of configuring the integration."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required("city"): str,
                    }
                ),
                errors={},
            )

        # Sprawdzamy miasto, które użytkownik wpisał
        city_name = user_input["city"]
        cities = await self._fetch_cities(city_name)

        if not cities:
            return self.async_show_form(
                step_id="user",
                errors={"city": "invalid_city"},
                data_schema=vol.Schema(
                    {
                        vol.Required("city"): str,
                    }
                ),
            )

        # Zamiast automatycznie wybierać miasto, umożliwiamy użytkownikowi wybór z listy
        city_choices = {
            city["Name"]: city  # Używamy nazwy miasta jako klucza do późniejszego zapisania danych
            for city in cities
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("selected_city"): vol.In(city_choices),  # Tworzymy pole z listą do wyboru
                }
            ),
            errors={},
            description_placeholders={"city_choices": ", ".join(city_choices.keys())},  # Opcjonalnie pokazujemy miasta w placeholderze
        )

    async def async_step_user_selected(self, user_input):
        """Handle the selected city and save the chosen one."""
        selected_city_name = user_input["selected_city"]
        city_data = next(
            city for city in cities if city["Name"] == selected_city_name
        )

        # Zapisz dane miasta
        return self.async_create_entry(
            title=city_data["Name"],  # Możesz zmienić to na jakąś preferowaną nazwę
            data=city_data,  # Zapisujemy cały obiekt JSON z odpowiedzi
        )
