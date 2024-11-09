import logging
import requests
from homeassistant.helpers.entity import Entity
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

class TauronOutageSensor(Entity):
    """Representation of a Tauron outage sensor."""

    def __init__(self, name, city_gaid, street_gaid, house_no, flat_no, update_interval):
        """Initialize the sensor."""
        self._name = name
        self._city_gaid = city_gaid
        self._street_gaid = street_gaid
        self._house_no = house_no
        self._flat_no = flat_no
        self._update_interval = update_interval
        self._state = None
        self._last_update = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    async def async_update(self):
        """Fetch the latest data from Tauron API."""
        now = datetime.utcnow()
        if self._last_update is None or now - self._last_update > timedelta(minutes=self._update_interval):
            url = f"https://www.tauron-dystrybucja.pl/waapi/outages/address?cityGAID={self._city_gaid}&streetGAID={self._street_gaid}&houseNo={self._house_no}&fromDate={now.isoformat()}&toDate={(now + timedelta(days=7)).isoformat()}&getLightingSupport=true&getServicedSwitchingoff=true"
            response = requests.get(url)
            if response.status_code == 200:
                outages = response.json()
                if outages:
                    self._state = outages[0]["Name"]
                else:
                    self._state = "No outage"
                self._last_update = now
            else:
                _LOGGER.error("Failed to fetch outage data")
