"""The Tauron Dystrybucja integration."""
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

PLATFORMS = ["sensor"]

_LOGGER = logging.getLogger(__name__)

DOMAIN = "tauron_dystrybucja"

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Tauron Dystrybucja integration."""
    _LOGGER.debug("Setting up Tauron Dystrybucja integration.")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Tauron Dystrybucja from a config entry."""
    _LOGGER.debug("Setting up Tauron Dystrybucja config entry.")
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
