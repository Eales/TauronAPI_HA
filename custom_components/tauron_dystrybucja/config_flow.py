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

        if user_input is not None:
            # Sprawdzamy miasto, które użytkownik wpisał
            city_name = user_input["city"]
            if len(city_name) >= 3:
                # Jeśli wpisano co najmniej 3 znaki, pobieramy listę miast
                cities = await self._fetch_cities(city_name)

                if cities:
                    # Zapisujemy listę miast w zmiennej instancyjnej
                    self.city_choices = {city["Name"]: city for city in cities}
                else:
                    errors["city"] = "invalid_city"
            else:
                self.city_choices = None
        else:
            self.city_choices = None

        data_schema = vol.Schema(
            {
                vol.Required("city"): str if not self.city_choices else vol.In(list(self.city_choices.keys())),
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
                        vol.Required("city"): vol.In(list(self.city_choices.keys())),  # Użytkownik musi wybrać wartość z listy
                    }
                ),
                errors={"city": "selection_required"},
            )

        selected_city_name = user_input["city"]
        city_data = self.city_choices[selected_city_name]

        # Zapisz dane miasta
        return self.async_create_entry(
            title=selected_city_name,  # Możesz zmienić to na jakąś preferowaną nazwę
            data=city_data,  # Zapisujemy cały obiekt JSON z odpowiedzi
        )
