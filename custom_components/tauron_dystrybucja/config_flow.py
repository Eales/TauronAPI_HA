import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
import aiohttp

from .const import DOMAIN

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Główny krok konfiguracji."""
        if user_input is not None:
            return await self.async_step_city()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
        )

    async def async_step_city(self, user_input=None):
        """Krok wybierania miejscowości."""
        errors = {}
        suggestions = []

        if user_input and "city" in user_input:
            city_query = user_input["city"]
            if len(city_query) >= 3:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f'https://www.tauron-dystrybucja.pl/waapi/enum/geo/cities?partName={city_query}'
                    ) as resp:
                        if resp.status == 200:
                            cities = await resp.json()
                            if cities:
                                suggestions = {city["GAID"]: city["Name"] for city in cities}
                                return self.async_show_form(
                                    step_id="city",
                                    data_schema=vol.Schema({
                                        vol.Required("city_gaid", default=next(iter(suggestions))): vol.In(suggestions),
                                    }),
                                )
                            else:
                                errors["base"] = "no_results"
                        else:
                            errors["base"] = "api_error"
            else:
                errors["base"] = "short_query"

        return self.async_show_form(
            step_id="city",
            data_schema=vol.Schema({
                vol.Required("city", description="Wprowadź minimum 3 znaki nazwy miejscowości"): str,
            }),
            errors=errors,
        )

    async def async_step_street(self, user_input=None):
        """Krok wybierania ulicy."""
        errors = {}
        suggestions = []

        if user_input and "street" in user_input:
            street_query = user_input["street"]
            city_gaid = self.context["city_gaid"]

            if len(street_query) >= 3:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f'https://www.tauron-dystrybucja.pl/waapi/enum/geo/streets?partName={street_query}&ownerGAID={city_gaid}'
                    ) as resp:
                        if resp.status == 200:
                            streets = await resp.json()
                            if streets:
                                suggestions = {street["GAID"]: street["Name"] for street in streets}
                                return self.async_show_form(
                                    step_id="street",
                                    data_schema=vol.Schema({
                                        vol.Required("street_gaid", default=next(iter(suggestions))): vol.In(suggestions),
                                    }),
                                )
                            else:
                                errors["base"] = "no_results"
                        else:
                            errors["base"] = "api_error"
            else:
                errors["base"] = "short_query"

        return self.async_show_form(
            step_id="street",
            data_schema=vol.Schema({
                vol.Required("street", description="Wprowadź minimum 3 znaki nazwy ulicy"): str,
            }),
            errors=errors,
        )

    async def async_step_house(self, user_input=None):
        """Krok wybierania numeru domu."""
        if user_input:
            return await self.async_step_flat()

        return self.async_show_form(
            step_id="house",
            data_schema=vol.Schema({
                vol.Required("house_no"): str,
            }),
        )

    async def async_step_flat(self, user_input=None):
        """Krok wybierania numeru mieszkania (opcjonalny)."""
        if user_input is not None:
            return self.async_create_entry(
                title="Konfiguracja Tauron Awarie",
                data=user_input,
            )

        return self.async_show_form(
            step_id="flat",
            data_schema=vol.Schema({
                vol.Optional("flat_no"): str,
            }),
        )
