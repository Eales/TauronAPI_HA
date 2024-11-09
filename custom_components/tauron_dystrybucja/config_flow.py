import logging
import voluptuous as vol
import aiohttp
from homeassistant import config_entries

_LOGGER = logging.getLogger(__name__)

class TauronConfigFlow(config_entries.ConfigFlow, domain="tauron"):
    """Konfiguracja integracji Tauron."""

    def __init__(self):
        """Inicjalizacja konfiguracji."""
        self.city_gaid = None
        self.street_gaid = None
        self.house_no = None
        self.flat_no = None

    async def async_step_city(self, user_input=None):
        """Pierwszy krok - wybór miasta."""
        if user_input is not None:
            self.city_gaid = user_input["city_gaid"]
            return await self.async_step_street()

        # Podpowiadanie miast
        return self.async_show_form(
            step_id="city",
            data_schema=vol.Schema({
                vol.Required("city_name"): str,
            }),
            custom_actions=self.async_get_cities,
        )

    async def async_get_cities(self, user_input):
        """Podpowiadanie miast z API Tauron."""
        if len(user_input["city_name"]) < 3:
            return []

        url = f"https://www.tauron-dystrybucja.pl/waapi/enum/geo/cities?partName={user_input['city_name']}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [{"label": city["Name"], "value": city["GUS"]} for city in data]
                    return []
            except Exception as e:
                _LOGGER.error("Błąd podczas pobierania miast: %s", e)
                return []

    async def async_step_street(self, user_input=None):
        """Drugi krok - wybór ulicy."""
        if user_input is not None:
            self.street_gaid = user_input["street_gaid"]
            return await self.async_step_house_no()

        # Podpowiadanie ulic po minimum 3 znakach
        return self.async_show_form(
            step_id="street",
            data_schema=vol.Schema({
                vol.Required("street_name"): str,
            }),
            custom_actions=self.async_get_streets,
        )

    async def async_get_streets(self, user_input):
        """Podpowiadanie ulic z API Tauron."""
        if len(user_input["street_name"]) < 3:
            return []

        url = f"https://www.tauron-dystrybucja.pl/waapi/enum/geo/streets?partName={user_input['street_name']}&ownerGAID={self.city_gaid}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [{"label": street["FullName"], "value": street["GAID"]} for street in data]
                    return []
            except Exception as e:
                _LOGGER.error("Błąd podczas pobierania ulic: %s", e)
                return []

    async def async_step_house_no(self, user_input=None):
        """Trzeci krok - wybór numeru domu."""
        if user_input is not None:
            self.house_no = user_input["house_no"]
            return await self.async_step_flat_no()

        # Podpowiadanie numerów domów
        return self.async_show_form(
            step_id="house_no",
            data_schema=vol.Schema({
                vol.Required("house_no"): str,
            }),
            custom_actions=self.async_get_house_numbers,
        )

    async def async_get_house_numbers(self, user_input):
        """Podpowiadanie numerów domów z API Tauron."""
        if len(user_input["house_no"]) < 1:
            return []

        url = f"https://www.tauron-dystrybucja.pl/waapi/enum/geo/housenumbers?partName={user_input['house_no']}&cityGAID={self.city_gaid}&streetGAID={self.street_gaid}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [{"label": str(house["HouseNumber"]), "value": house["HouseNumber"]} for house in data]
                    return []
            except Exception as e:
                _LOGGER.error("Błąd podczas pobierania numerów domów: %s", e)
                return []

    async def async_step_flat_no(self, user_input=None):
        """Czwarty krok - opcjonalny numer mieszkania."""
        if user_input is not None:
            self.flat_no = user_input["flat_no"]
            return self.async_create_entry(title="Tauron Integration", data={
                "city_gaid": self.city_gaid,
                "street_gaid": self.street_gaid,
                "house_no": self.house_no,
                "flat_no": self.flat_no,
            })

        # Podpowiadanie numerów mieszkań
        return self.async_show_form(
            step_id="flat_no",
            data_schema=vol.Schema({
                vol.Optional("flat_no"): str,
            }),
            custom_actions=self.async_get_flat_numbers,
        )

    async def async_get_flat_numbers(self, user_input):
        """Podpowiadanie numerów mieszkań z API Tauron."""
        if len(user_input.get("flat_no", "")) < 1:
            return []

        url = f"https://www.tauron-dystrybucja.pl/waapi/enum/geo/flatnumbers?partName={user_input['flat_no']}&cityGAID={self.city_gaid}&streetGAID={self.street_gaid}&houseNo={self.house_no}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [{"label": str(flat["FlatNumber"]), "value": flat["FlatNumber"]} for flat in data]
                    return []
            except Exception as e:
                _LOGGER.error("Błąd podczas pobierania numerów mieszkań: %s", e)
                return []
