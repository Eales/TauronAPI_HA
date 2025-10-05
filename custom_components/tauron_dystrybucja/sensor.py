import logging
from datetime import timedelta, datetime
from typing import Any, Dict, List

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TauronOutagesCoordinator(DataUpdateCoordinator[List[Dict[str, Any]]]):
    """Coordinator to fetch outages from Tauron API."""

    def __init__(
        self,
        hass: HomeAssistant,
        city_gaid: str,
        street_gaid: str,
        house_number: str,
        update_interval_minutes: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Tauron Dystrybucja Outages",
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self._city_gaid = city_gaid
        self._street_gaid = street_gaid
        self._house_number = house_number

    async def _async_update_data(self) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        url = (
            "https://www.tauron-dystrybucja.pl/waapi/outages/address"
            f"?cityGAID={self._city_gaid}"
            f"&streetGAID={self._street_gaid}"
            f"&houseNo={self._house_number}"
            f"&fromDate={now.isoformat()}"
            f"&toDate={(now + timedelta(days=7)).isoformat()}"
            "&getLightingSupport=true&getServicedSwitchingoff=true"
        )
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                if isinstance(data, list):
                    return data
                return []
        except Exception as err:  # noqa: BLE001 - surface all errors to logs
            _LOGGER.error("Failed to fetch outage data: %s", err)
            return []


class TauronOutageSensor(CoordinatorEntity[TauronOutagesCoordinator], SensorEntity):
    """Sensor representing next outage information."""

    _attr_icon = "mdi:transmission-tower"

    def __init__(
        self,
        coordinator: TauronOutagesCoordinator,
        name: str,
        unique_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = unique_id

    @property
    def native_value(self) -> str | None:
        outages = self.coordinator.data or []
        if outages:
            first = outages[0]
            return first.get("Name") or first.get("name")
        return "No outage"


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up Tauron outage sensor from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    city_gaid = data.get("city_gaid") or data.get("city")
    street_gaid = data.get("street_gaid") or data.get("street")
    house_number = data.get("house_number")
    update_interval = int(data.get("update_interval", 30))

    coordinator = TauronOutagesCoordinator(
        hass,
        city_gaid=city_gaid,
        street_gaid=street_gaid,
        house_number=house_number,
        update_interval_minutes=update_interval,
    )
    await coordinator.async_config_entry_first_refresh()

    sensor = TauronOutageSensor(
        coordinator,
        name="Tauron Outage",
        unique_id=f"{city_gaid}-{street_gaid}-{house_number}",
    )
    async_add_entities([sensor])
