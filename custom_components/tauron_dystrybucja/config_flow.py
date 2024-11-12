import aiohttp
import logging
from homeassistant import config_entries
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://www.tauron-dystrybucja.pl"  # Zaktualizowany URL bazowy

class TauronConfigFlow(config_entries.ConfigFlow, domain="tauron_dystrybucja"):
    """Handle a config flow for Tauron Dystrybucja."""
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
        if len(city_name) < 3:
            # Jeśli wpisano mniej niż 3 znaki, zwracamy to, co użytkownik wpisał i nie wykonujemy zapytania do API
            return self.async_show_form(
                step_id="user",
                errors={},
                data_schema=vol.Schema(
                    {
                        vol.Required("city", default=city_name): str,
                    }
                ),
            )

        # Jeśli wpisano co najmniej 3 znaki, pobieramy listę miast
        cities = await self._fetch_cities(city_name)

        if not cities:
            return self.async_show_form(
                step_id="user",
                errors={"city": "invalid_city"},
                data_schema=vol.Schema(
                    {
                        vol.Required("city", default=city_name): str,
                    }
                ),
            )

        # Zamiast automatycznie przechodzić do nowego kroku, umożliwiamy użytkownikowi wybór z listy w tym samym polu
        city_choices = {
            city["Name"]: city for city in cities  # Używamy nazwy miasta jako klucza do późniejszego zapisania danych
        }

        # Dodajemy pole, które dynamicznie aktualizuje podpowiedzi na podstawie wyników API
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("city"): vol.In(list(city_choices.keys()) if len(city_choices) > 0 else [city_name]),  # Podpowiedzi dynamicznie aktualizowane po wpisaniu 3 znaków
                }
            ),
            errors={},
        )

    async def async_step_user_selected(self, user_input):
        """Handle the selected city and save the chosen one."""
        selected_city_name = user_input["city"]
        city_data = await self._fetch_cities(selected_city_name)

        if not city_data:
            return self.async_show_form(
                step_id="user",
                errors={"city": "invalid_city"},
                data_schema=vol.Schema(
                    {
                        vol.Required("city"): str,
                    }
                ),
            )

        # Zapisz dane miasta
        return self.async_create_entry(
            title=selected_city_name,  # Możesz zmienić to na jakąś preferowaną nazwę
            data=city_data[0],  # Zapisujemy pierwszy dopasowany obiekt JSON z odpowiedzi
        )
