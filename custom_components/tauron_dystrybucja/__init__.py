"""The Tauron Dystrybucja integration."""
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import discovery

_LOGGER = logging.getLogger(__name__)

DOMAIN = "tauron_dystrybucja"

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Tauron Dystrybucja integration."""
    _LOGGER.debug("Setting up Tauron Dystrybucja integration.")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Tauron Dystrybucja from a config entry."""
    _LOGGER.debug("Setting up Tauron Dystrybucja config entry.")
    hass.data[DOMAIN] = entry.data
    # Discover the entities based on the config entry
    return True
