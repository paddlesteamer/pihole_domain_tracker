"""The pihole domain tracker integration."""
from __future__ import annotations
from typing import List
from datetime import timedelta

import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_CLIENT_ADDRESS, COORDINATOR, DOMAIN, LAST_CHECKED
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_ADDRESS

import logging
import time
import requests

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:

    poller = PiHoleTracker(
        hass, config.data[CONF_ADDRESS], config.data[CONF_ACCESS_TOKEN], config.data[CONF_CLIENT_ADDRESS]
    )

    coordinator = ApiCoordinator(hass, poller)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config.entry_id] = {COORDINATOR: coordinator}

    hass.config_entries.async_setup_platforms(config, ["sensor"])

    return True


class ApiCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, pihole):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Api Coordinator",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=5),
        )
        self.pihole = pihole

    async def _async_update_data(self):
        """Fetch data from API endpoint."""

        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                return await self.pihole.check()

        except Exception as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            _LOGGER.error(err)
            raise ConfigEntryAuthFailed from err


class PiHoleTracker:
    def __init__(self, hass: HomeAssistant, addr: str, token: str, client: str) -> None:
        self.hass = hass

        self.addr = addr
        self.token = token
        self.client = client

        self.timestamp = int(time.time())

    async def _query(self) -> List:
        payload = {
            "getAllQueries": 1,
            "auth": self.token,
            "domain": "sg.business.smartcamera.api.io.mi.com",
            "client": self.client,
        }

        r = await self.hass.async_add_executor_job(
            requests.get, f"http://{self.addr}/admin/api.php", payload
        )

        if r.status_code != 200:
            _LOGGER.error(f"PiHole returned: {r.status_code}")
            return []

        return r.json()["data"]

    async def check(self):
        queries = await self._query()

        data = {LAST_CHECKED: time.ctime()}

        if len(queries) == 0:
            _LOGGER.debug("No queries found")
            return data

        ts = int(queries[-1][0])

        _LOGGER.debug(f"Last query: {ts}, current: {self.timestamp}")

        if ts - self.timestamp <= 30:
            return data

        self.timestamp = ts

        _LOGGER.info("Query detected")

        ## fire event
        self.hass.bus.async_fire(
            f"{DOMAIN}_query_detected_event", {"time": time.ctime()}
        )

        return data
