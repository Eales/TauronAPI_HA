import aiohttp
import logging
from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers.selector import selector

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
        errors = {}

        city_name = ""
        city_choices = []

        if user_input is not None:
            # Sprawdzamy miasto, które użytkownik wpisał
            city_name = user_input.get("city", "")
            if len(city_name) >= 3:
                # Jeśli wpisano co najmniej 3 znaki, pobieramy listę miast
                cities = await self._fetch_cities(city_name)

                if cities:
                    city_choices = [city["Name"] for city in cities]
                else:
                    city_choices = []  # Jeśli nie ma wyników, pozostawiamy listę pustą
            else:
                city_choices = []  # Jeśli za mało znaków, lista pozostaje pusta
        
        # Pozwalamy użytkownikowi wpisać cokolwiek, ale po wpisaniu 3 znaków oferujemy podpowiedzi
        data_schema = vol.Schema(
            {
                vol.Required("city", default=city_name): str,
            }
        )

        if len(city_name) >= 3 and city_choices:
            # Dodajemy listę wyboru jako podpowiedzi, ale pozwalamy na wpisywanie dowolnego tekstu
            data_schema = vol.Schema(
                {
                    vol.Required("city", default=city_name): vol.Any(vol.In(city_choices), str),
                }
            )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_user_selected(self, user_input):
        """Handle the selected city and save the chosen one."""
        if not user_input or "city" not in user_input:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required("city"): str,
                    }
                ),
                errors={"city": "selection_required"},
            )

        selected_city_name = user_input["city"]
        cities = await self._fetch_cities(selected_city_name)
        city_data = next((city for city in cities if city["Name"] == selected_city_name), None)

        if not city_data:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required("city"): str,
                    }
                ),
                errors={"city": "invalid_city"},
            )

        # Zapisz dane miasta
        return self.async_create_entry(
            title=selected_city_name,  # Możesz zmienić to na jakąś preferowaną nazwę
            data=city_data,  # Zapisujemy cały obiekt JSON z odpowiedzi
        )
