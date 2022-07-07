"""Config flow for pihole domain tracker integration."""
from __future__ import annotations

import logging
from typing import Any
import requests

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_CLIENT_ADDRESS, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ADDRESS): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Required(CONF_CLIENT_ADDRESS): str,
    }
)


class Validator:
    """Validator class."""

    def __init__(self, hass: HomeAssistant, addr: str, token: str) -> None:
        """Initialize."""
        self.hass = hass
        self.addr = addr
        self.token = token

    async def connect(self) -> bool:
        r = await self.hass.async_add_executor_job(
            requests.get,
            f"http://{self.addr}/admin/api.php",
        )

        return r.status_code == 200

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""
        payload = {"getAllQueries": "1", "auth": self.token}

        r = await self.hass.async_add_executor_job(
            requests.get, f"http://{self.addr}/admin/api.php", payload
        )

        if r.status_code != 200:
            return False

        return "data" in r.json()


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    hub = Validator(hass, data[CONF_ADDRESS], data[CONF_ACCESS_TOKEN])

    if not await hub.connect():
        raise CannotConnect

    if not await hub.authenticate():
        raise InvalidAuth

    return {
        "title": "PiHole Domain Tracker",
        CONF_ADDRESS: data[CONF_ADDRESS],
        CONF_ACCESS_TOKEN: data[CONF_ACCESS_TOKEN],
        CONF_CLIENT_ADDRESS: data[CONF_CLIENT_ADDRESS],
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for pihole domain tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
