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
        city_choices = []

        # Sprawdzanie wprowadzonego inputu
        if user_input is not None:
            city_name = user_input.get("city", "")
            if len(city_name) >= 3:
                # Jeśli wpisano przynajmniej 3 znaki, pobieramy miasta
                cities = await self._fetch_cities(city_name)
                if cities:
                    city_choices = [city["Name"] for city in cities]
                    # Przechodzimy do kroku wyboru z listy miast
                    return await self.async_step_city_selection(city_choices, city_name)
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
            description_placeholders={
                "label_city": "Wprowadź przynajmniej 3 litery nazwy miasta, aby wybrać z dostępnych opcji."
            },
            step_description="Proszę wpisać nazwę miasta (minimum 3 znaki), a następnie kliknąć 'Dalej'."
        )

    async def async_step_city_selection(self, city_choices, default_city):
        """Handle the step where the user selects a city from the list."""
        data_schema = vol.Schema(
            {
                vol.Required("city", default=default_city): vol.In(city_choices),
            }
        )

        return self.async_show_form(
            step_id="city_selection",
            data_schema=data_schema,
            errors={},
            description_placeholders={
                "label_city_selection": "Wybierz odpowiednie miasto z poniższej listy."
            },
            step_description="Wybierz miasto z listy poniżej, a następnie kliknij 'Dalej'. Aby wrócić do poprzedniego kroku, kliknij 'Cofnij'.",
            last_step=False,
            show_previous=True  # Dodanie przycisku 'Cofnij'
        )

    async def async_step_city_selection_complete(self, user_input=None):
        """Complete the city selection and create the entry."""
        if user_input is None or "city" not in user_input:
            return self.async_show_form(
                step_id="city_selection",
                data_schema=vol.Schema(
                    {
                        vol.Required("city"): str,
                    }
                ),
                errors={"city": "selection_required"},
                description_placeholders={
                    "label_selection_required": "Proszę dokonać wyboru z listy miast przed kontynuacją."
                },
                step_description="Proszę wybrać miasto, aby kontynuować. Aby wrócić do poprzedniego kroku, kliknij 'Cofnij'.",
                last_step=False,
                show_previous=True  # Dodanie przycisku 'Cofnij'
            )

        selected_city_name = user_input["city"]
        cities = await self._fetch_cities(selected_city_name)
        city_data = next((city for city in cities if city["Name"] == selected_city_name), None)

        if not city_data:
            # Tworzymy dane na podstawie wprowadzonego miasta
            city_data = {"Name": selected_city_name}

        # Tworzymy wpis konfiguracyjny
        return self.async_create_entry(
            title=selected_city_name,
            data=city_data,
        )

# Jak tego używać:
# 1. Najpierw użytkownik wprowadza początkowe litery miasta.
# 2. System sprawdza wprowadzone dane, jeśli ma minimum 3 znaki.
# 3. Wyświetlana jest lista podpowiedzi, z której użytkownik może wybrać odpowiednie miasto.
# 4. Po zatwierdzeniu formularza, miasto zostaje wybrane i utworzony jest wpis konfiguracyjny.
# 5. Użytkownik może wrócić do poprzedniego kroku, klikając 'Cofnij'.
# 
# Uwagi: Pełne autouzupełnianie nie jest możliwe w Home Assistant bez dostępu do frontendu.
# Ten kod stanowi obejście, które pozwala na wybór miasta w sposób podobny do funkcji autouzupełniania.
