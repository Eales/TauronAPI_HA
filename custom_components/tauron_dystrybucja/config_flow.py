import logging
import requests
from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

class TauronDstrybucjaConfigFlow(config_entries.ConfigFlow, domain="tauron_dystrybucja"):
    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        self._user_input = {}

    async def async_step_user(self, user_input=None):
        """Handle the user input during the setup."""
        if user_input is not None:
            # Zbieranie danych użytkownika
            self._user_input = user_input
            
            # Weryfikacja danych miejscowości
            if not await self._validate_city(user_input['city']):
                errors = {"base": "invalid_city"}
                return self.async_show_form(step_id="user", data_schema=self._get_schema(), errors=errors)
            
            # Weryfikacja ulicy
            if not await self._validate_street(user_input['street']):
                errors = {"base": "invalid_street"}
                return self.async_show_form(step_id="user", data_schema=self._get_schema(), errors=errors)
            
            # Weryfikacja numeru domu
            if not await self._validate_house_number(user_input['house_no']):
                errors = {"base": "invalid_house_number"}
                return self.async_show_form(step_id="user", data_schema=self._get_schema(), errors=errors)

            # Zapis konfiguracji
            return self.async_create_entry(
                title="Tauron Dystrybucja",
                data=self._user_input
            )

        # Jeśli dane nie zostały wprowadzone, wyświetl formularz
        return self.async_show_form(step_id="user", data_schema=self._get_schema())

    def _get_schema(self):
        """Return the data schema for the form."""
        return vol.Schema({
            vol.Required('city'): cv.string,
            vol.Required('street'): cv.string,
            vol.Required('house_no'): cv.string,
            vol.Optional('flat_no'): cv.string,
            vol.Optional(CONF_SCAN_INTERVAL, default=60): cv.positive_int,  # Interwał sprawdzania w minutach
        })
    
    async def _validate_city(self, city_name):
        """Weryfikacja miejscowości na podstawie API."""
        url = f"https://www.tauron-dystrybucja.pl/waapi/enum/geo/cities?partName={city_name}"
        response = requests.get(url)
        return response.status_code == 200 and len(response.json()) > 0

    async def _validate_street(self, street_name):
        """Weryfikacja ulicy na podstawie API."""
        city_id = self._user_input['city_id']
        url = f"https://www.tauron-dystrybucja.pl/waapi/enum/geo/streets?partName={street_name}&ownerGAID={city_id}"
        response = requests.get(url)
        return response.status_code == 200 and len(response.json()) > 0
    
    async def _validate_house_number(self, house_number):
        """Weryfikacja numeru domu na podstawie API."""
        city_id = self._user_input['city_id']
        street_id = self._user_input['street_id']
        url = f"https://www.tauron-dystrybucja.pl/waapi/enum/geo/housenumbers?partName={house_number}&cityGAID={city_id}&streetGAID={street_id}"
        response = requests.get(url)
        return response.status_code == 200 and len(response.json()) > 0
