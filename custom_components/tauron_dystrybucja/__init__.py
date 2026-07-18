"""The Tauron Dystrybucja integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TauronApi, TauronApiError
from .const import (
    CONF_CITY_GAID,
    CONF_CITY_NAME,
    CONF_HOUSE_NO,
    CONF_STREET_GAID,
    CONF_STREET_NAME,
    DOMAIN,
)
from .coordinator import TauronOutageCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "calendar", "event", "sensor"]

type TauronConfigEntry = ConfigEntry[TauronOutageCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: TauronConfigEntry) -> bool:
    """Set up Tauron Dystrybucja from a config entry."""
    coordinator = TauronOutageCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # The polling interval lives in options, so re-read it when they change.
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: TauronConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: TauronConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate v1 entries, which stored plain names instead of GAIDs."""
    if entry.version >= 2:
        return True

    api = TauronApi(async_get_clientsession(hass))
    city_name = entry.data.get("city")
    street_name = entry.data.get("street")
    house_no = entry.data.get("house_number")

    if not city_name or not street_name or not house_no:
        _LOGGER.error("Cannot migrate entry %s: incomplete address, please re-add it", entry.title)
        return False

    try:
        cities = await api.async_get_cities(city_name)
        city = next((c for c in cities if c.get("Name") == city_name), None)
        if city is None:
            _LOGGER.error("Cannot migrate entry %s: city %s not found", entry.title, city_name)
            return False

        streets = await api.async_get_streets(city["GAID"], street_name)
        street = next((s for s in streets if s.get("Name") == street_name), None)
        if street is None:
            _LOGGER.error(
                "Cannot migrate entry %s: street %s not found in %s",
                entry.title,
                street_name,
                city_name,
            )
            return False
    except TauronApiError as err:
        raise ConfigEntryNotReady(f"Tauron API unavailable during migration: {err}") from err

    hass.config_entries.async_update_entry(
        entry,
        version=2,
        unique_id=f"{city['GAID']}-{street['GAID']}-{house_no}",
        data={
            CONF_CITY_NAME: city_name,
            CONF_CITY_GAID: city["GAID"],
            CONF_STREET_NAME: street_name,
            CONF_STREET_GAID: street["GAID"],
            CONF_HOUSE_NO: str(house_no),
        },
    )
    _LOGGER.info("Migrated Tauron Dystrybucja entry %s to version 2", entry.title)
    return True
