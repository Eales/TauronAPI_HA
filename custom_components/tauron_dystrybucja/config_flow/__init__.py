"""Handle the config flow for Tauron Dystrybucja."""
import logging
import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "tauron_dystrybucja"

class TauronConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tauron Dystrybucja integration."""

    async def async_step_user(self, user_input=None):
        """Handle the user input for configuration."""
        errors = {}
        
        if user_input is not None:
            city_name = user_input["city_name"]
            street_name = user_input["street_name"]
            house_no = user_input["house_no"]
            flat_no = user_input.get("flat_no", "")
            
            # Get City and Street data from Tauron API
            city_data = self.get_city_data(city_name)
            street_data = self.get_street_data(street_name, city_data["GUS"])

            if not city_data or not street_data:
                errors["base"] = "invalid_city_or_street"
            else:
                return self.async_create_entry(
                    title=f"{city_name} - {street_name}",
                    data={
                        "city_name": city_name,
                        "street_name": street_name,
                        "house_no": house_no,
                        "flat_no": flat_no,
                    },
                )
        
        return self.async_show_form(
            step_id="user", 
            data_schema=self.get_schema(),
            errors=errors
        )

    def get_schema(self):
        """Return schema for the user input form."""
        return vol.Schema({
            vol.Required("city_name"): str,
            vol.Required("street_name"): str,
            vol.Required("house_no"): str,
            vol.Optional("flat_no", default=""): str,
        })

    def get_city_data(self, city_name):
        """Query Tauron API to get city data."""
        url = f"https://www.tauron-dystrybucja.pl/waapi/enum/geo/cities?partName={city_name}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()[0]  # Return first match
        return None

    def get_street_data(self, street_name, city_gus):
        """Query Tauron API to get street data."""
        url = f"https://www.tauron-dystrybucja.pl/waapi/enum/geo/streets?partName={street_name}&ownerGAID={city_gus}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()[0]  # Return first match
        return None
