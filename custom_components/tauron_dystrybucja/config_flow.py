import aiohttp
import logging
from homeassistant import config_entries
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://www.tauron-dystrybucja.pl"

class TauronConfigFlow(config_entries.ConfigFlow, domain="tauron_dystrybucja"):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def _fetch(self, endpoint, params):
        url = f"{API_BASE_URL}{endpoint}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data if isinstance(data, list) else []
            except aiohttp.ClientError as e:
                _LOGGER.error(f"Client error fetching data: {e}")
                return []
            except Exception as e:
                _LOGGER.error(f"Unexpected error fetching data: {e}")
                return []

async def async_step_user(self, user_input=None):
    errors = {}
    if user_input:
        city_partial = user_input["city_partial"]
        if len(city_partial) >= 3:
            cities = await self._fetch("/waapi/enum/geo/cities", {"partName": city_partial})
            if cities:
                self.city_choices = [city["Name"] for city in cities]
                return await self.async_step_city_selection(user_input=None)
            errors["city_partial"] = "no_cities_found"
        else:
            errors["city_partial"] = "too_few_characters"

    schema = vol.Schema({vol.Required("city_partial"): str})
    return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

async def async_step_city_selection(self, user_input=None):
    errors = {}
    if user_input:
        selected_city = user_input["selected_city"]
        if selected_city == "back":
            return await self.async_step_user(user_input=None)
        if selected_city in self.city_choices:
            self.selected_city = selected_city
            return await self.async_step_street(user_input=None)
        errors["selected_city"] = "invalid_city_selection"

    schema = vol.Schema({
        vol.Required("selected_city"): vol.In(self.city_choices + ["back"])
    })
    return self.async_show_form(step_id="city_selection", data_schema=schema, errors=errors, last_step=False)

async def async_step_street(self, user_input=None):
    errors = {}
    if user_input:
        street_partial = user_input["street_partial"]
        if len(street_partial) >= 3:
            streets = await self._fetch("/waapi/enum/geo/streets", {
                "cityName": self.selected_city,
                "partName": street_partial
            })
            if streets:
                self.street_choices = [street["Name"] for street in streets]
                return await self.async_step_street_selection(user_input=None)
            errors["street_partial"] = "no_streets_found"
        else:
            errors["street_partial"] = "too_few_characters"

    schema = vol.Schema({vol.Required("street_partial"): str})
    return self.async_show_form(step_id="street", data_schema=schema, errors=errors, last_step=False)

async def async_step_street_selection(self, user_input=None):
    errors = {}
    if user_input:
        selected_street = user_input["selected_street"]
        if selected_street == "back":
            return await self.async_step_street(user_input=None)
        if selected_street in self.street_choices:
            self.selected_street = selected_street
            return await self.async_step_house_number(user_input=None)
        errors["selected_street"] = "invalid_street_selection"

    schema = vol.Schema({
        vol.Required("selected_street"): vol.In(self.street_choices + ["back"])
    })
    return self.async_show_form(step_id="street_selection", data_schema=schema, errors=errors, last_step=False)

async def async_step_house_number(self, user_input=None):
    errors = {}
    if user_input:
        house_number = user_input["house_number"]
        if house_number:
            return self.async_create_entry(
                title=f"{self.selected_city}, {self.selected_street} {house_number}",
                data={
                    "city": self.selected_city,
                    "street": self.selected_street,
                    "house_number": house_number
                }
            )
        errors["house_number"] = "invalid_house_number"

    schema = vol.Schema({
        vol.Required("house_number"): str
    })
    return self.async_show_form(step_id="house_number", data_schema=schema, errors=errors, last_step=False)
