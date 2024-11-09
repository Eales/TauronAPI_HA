import logging
import requests
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

# Tauron API endpoints
API_BASE_URL = "https://www.tauron-dystrybucja.pl/waapi/enum/geo"

class TauronConfigFlow(config_entries.ConfigFlow, domain="tauron"):
    """Handle a config flow for Tauron."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize the configuration flow."""
        self._city_data = None
        self._street_data = None
        self._house_number_data = None
        self._flat_number_data = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step of configuring the integration."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required("city"): str,
                        vol.Required("street"): str,
                    }
                ),
            )

        city = user_input["city"]
        street = user_input["street"]

        # Validate the city
        cities = await self._fetch_cities(city)
        if not cities:
            return self.async_show_form(
                step_id="user",
                errors={"city": "invalid_city"},
                data_schema=vol.Schema(
                    {
                        vol.Required("city"): str,
                        vol.Required("street"): str,
                    }
                ),
            )

        self._city_data = cities
        self._street_data = await self._fetch_streets(street, cities[0]["GAID"])

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("city"): city,
                    vol.Required("street"): street,
                    vol.Required("house_number"): str,
                }
            ),
            description_placeholders={"city": city, "street": street},
        )

    async def async_step_house_number(self, user_input=None):
        """Handle the house number input."""
        if user_input is None:
            return self.async_show_form(
                step_id="house_number",
                data_schema=vol.Schema(
                    {
                        vol.Required("house_number"): str,
                    }
                ),
            )

        house_number = user_input["house_number"]
        house_data = await self._fetch_house_numbers(
            house_number, self._city_data[0]["GAID"], self._street_data[0]["GAID"]
        )
        if not house_data:
            return self.async_show_form(
                step_id="house_number",
                errors={"house_number": "invalid_house_number"},
                data_schema=vol.Schema(
                    {
                        vol.Required("house_number"): str,
                    }
                ),
            )

        self._house_number_data = house_data

        return self.async_show_form(
            step_id="flat_number",
            data_schema=vol.Schema(
                {
                    vol.Optional("flat_number"): str,
                }
            ),
        )

    async def async_step_flat_number(self, user_input=None):
        """Handle the flat number input."""
        if user_input is None:
            return self.async_show_form(
                step_id="flat_number",
                data_schema=vol.Schema(
                    {
                        vol.Optional("flat_number"): str,
                    }
                ),
            )

        flat_number = user_input.get("flat_number", "")
        self._flat_number_data = flat_number

        # Store the configuration
        await self.async_set_unique_id(self._city_data[0]["GUS"])
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="Tauron Integration",
            data={
                "city": self._city_data[0]["Name"],
                "street": self._street_data[0]["Name"],
                "house_number": self._house_number_data[0]["FullName"],
                "flat_number": self._flat_number_data,
            },
        )

    async def _fetch_cities(self, city_name):
        """Fetch city list from Tauron API."""
        url = f"{API_BASE_URL}/cities?partName={city_name}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error fetching cities: {e}")
            return []

    async def _fetch_streets(self, street_name, city_gaid):
        """Fetch streets list from Tauron API."""
        url = f"{API_BASE_URL}/streets?partName={street_name}&ownerGAID={city_gaid}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error fetching streets: {e}")
            return []

    async def _fetch_house_numbers(self, house_number, city_gaid, street_gaid):
        """Fetch house numbers list from Tauron API."""
        url = f"{API_BASE_URL}/housenumbers?partName={house_number}&cityGAID={city_gaid}&streetGAID={street_gaid}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error fetching house numbers: {e}")
            return []

    async def _fetch_flat_numbers(self, flat_number, city_gaid, street_gaid, house_no):
        """Fetch flat numbers list from Tauron API."""
        url = f"{API_BASE_URL}/flatnumbers?partName={flat_number}&cityGAID={city_gaid}&streetGAID={street_gaid}&houseNo={house_no}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error fetching flat numbers: {e}")
            return []
