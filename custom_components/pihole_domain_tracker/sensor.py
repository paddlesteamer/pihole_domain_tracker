from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN, LAST_CHECKED


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entries
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    async_add_entries([PiHoleLastCheckedEntity(coordinator)])


class PiHoleLastCheckedEntity(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)

        self._attr_name = "PiHole Tracker Last Checked"

    def _handle_coordinator_update(self) -> None:
        self._attr_state = self.coordinator.data[LAST_CHECKED]
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self.coordinator.data[LAST_CHECKED]
