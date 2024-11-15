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
                    if not isinstance(data, list):
                        raise ValueError("Invalid response format")
                    _LOGGER.debug(f"Fetched cities data: {data}")  # Logowanie odpowiedzi
                    return data
            except aiohttp.ClientError as e:
                _LOGGER.error(f"Client error fetching cities: {e}")
                return []
            except Exception as e:
                _LOGGER.error(f"Unexpected error fetching cities: {e}")
                return []

    async def async_step_user(self, user_input=None):
        """Handle the initial step of configuring the integration."""
        errors = {}
        city_name = ""

        # Sprawdzanie wprowadzonego inputu
        if user_input is not None:
            city_name = user_input.get("city", "")
            if len(city_name) >= 3:
                # Jeśli wpisano przynajmniej 3 znaki, pobieramy miasta
                cities = await self._fetch_cities(city_name)
                if cities:
                    city_choices = [city["Name"] for city in cities]
                    # Przechodzimy do kroku wyboru z listy miast
                    self.city_choices = city_choices  # Zapiszemy dostępne miasta, aby ułatwić powrót
                    return await self.async_step_city_selection(user_input)
                else:
                    errors["city"] = "no_cities_found"  # Jeśli brak wyników
            else:
                errors["city"] = "too_few_characters"  # Gdy za mało znaków

        # Schemat początkowy - wpisanie początkowych znaków miasta
        data_schema = vol.Schema(
            {
                vol.Required("city", default=city_name): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_city_selection(self, user_input):
        """Handle the step where the user selects a city from the list."""
        errors = {}

        # Obsługa przycisku 'cofnij' - powrót do poprzedniego kroku
        if user_input is not None:
            selected_city = user_input.get("city")
            if selected_city == "back":
                return await self.async_step_user()

            # Jeśli miasto zostało wybrane, kończymy proces wyboru
            if selected_city in self.city_choices:
                return await self.async_step_city_selection_complete(user_input)
            else:
                errors["city"] = "invalid_city_selection"

        # Przycisk 'cofnij' dodawany do opcji wyboru
        city_choices = self.city_choices + ["back"]
        data_schema = vol.Schema(
            {
                vol.Required("city"): vol.In(city_choices),
            }
        )

        return self.async_show_form(
            step_id="city_selection",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_city_selection_complete(self, user_input):
        """Complete the city selection and create the entry."""
        selected_city_name = user_input["city"]

        # Tworzymy dane na podstawie wprowadzonego miasta
        city_data = {"Name": selected_city_name}

        # Tworzymy wpis konfiguracyjny
        return self.async_create_entry(
            title=selected_city_name,
            data=city_data,
        )
