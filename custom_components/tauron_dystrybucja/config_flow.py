import logging
from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://www.tauron-dystrybucja.pl"


class TauronConfigFlow(config_entries.ConfigFlow, domain="tauron_dystrybucja"):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def _fetch(self, endpoint: str, params: dict) -> list:
        """Fetch list data from Tauron API, returning list or empty list on error."""
        url = f"{API_BASE_URL}{endpoint}"
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                return data if isinstance(data, list) else []
        except Exception as err:  # noqa: BLE001 - log unexpected
            _LOGGER.error("Error fetching data from %s: %s", endpoint, err)
            return []

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input:
            city_partial: str = user_input["city_partial"].strip()
            if len(city_partial) >= 3:
                cities = await self._fetch("/waapi/enum/geo/cities", {"partName": city_partial})
                if cities:
                    # Map displayed names to GAIDs so we can retrieve the ids later
                    self.city_choices = {c.get("Name"): c.get("GAID") for c in cities if c.get("Name") and c.get("GAID")}
                    return await self.async_step_city_selection(user_input=None)
                errors["city_partial"] = "no_cities_found"
            else:
                errors["city_partial"] = "too_few_characters"

        schema = vol.Schema({vol.Required("city_partial"): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_city_selection(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input:
            selected_city_name = user_input["selected_city"]
            if selected_city_name == "back":
                return await self.async_step_user(user_input=None)
            if selected_city_name in self.city_choices:
                self.selected_city_name = selected_city_name
                self.selected_city_gaid = self.city_choices[selected_city_name]
                return await self.async_step_street(user_input=None)
            errors["selected_city"] = "invalid_city_selection"

        schema = vol.Schema({
            vol.Required("selected_city"): vol.In(list(self.city_choices.keys()) + ["back"])
        })
        return self.async_show_form(
            step_id="city_selection", data_schema=schema, errors=errors, last_step=False
        )

    async def async_step_street(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input:
            street_partial: str = user_input["street_partial"].strip()
            if len(street_partial) >= 3:
                streets = await self._fetch(
                    "/waapi/enum/geo/streets",
                    {"cityGAID": self.selected_city_gaid, "partName": street_partial},
                )
                if streets:
                    self.street_choices = {s.get("Name"): s.get("GAID") for s in streets if s.get("Name") and s.get("GAID")}
                    return await self.async_step_street_selection(user_input=None)
                errors["street_partial"] = "no_streets_found"
            else:
                errors["street_partial"] = "too_few_characters"

        schema = vol.Schema({vol.Required("street_partial"): str})
        return self.async_show_form(step_id="street", data_schema=schema, errors=errors, last_step=False)

    async def async_step_street_selection(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input:
            selected_street_name = user_input["selected_street"]
            if selected_street_name == "back":
                return await self.async_step_street(user_input=None)
            if selected_street_name in self.street_choices:
                self.selected_street_name = selected_street_name
                self.selected_street_gaid = self.street_choices[selected_street_name]
                return await self.async_step_house_number(user_input=None)
            errors["selected_street"] = "invalid_street_selection"

        schema = vol.Schema({
            vol.Required("selected_street"): vol.In(list(self.street_choices.keys()) + ["back"])
        })
        return self.async_show_form(
            step_id="street_selection", data_schema=schema, errors=errors, last_step=False
        )

    async def async_step_house_number(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input:
            house_number = user_input["house_number"].strip()
            if house_number:
                # Prevent duplicate entries for same location
                unique_id = f"{self.selected_city_gaid}-{self.selected_street_gaid}-{house_number}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"{self.selected_city_name}, {self.selected_street_name} {house_number}",
                    data={
                        "city_gaid": self.selected_city_gaid,
                        "street_gaid": self.selected_street_gaid,
                        "city_name": self.selected_city_name,
                        "street_name": self.selected_street_name,
                        "house_number": house_number,
                        "update_interval": 30,
                    },
                )
            errors["house_number"] = "invalid_house_number"

        schema = vol.Schema({vol.Required("house_number"): str})
        return self.async_show_form(
            step_id="house_number", data_schema=schema, errors=errors, last_step=False
        )
