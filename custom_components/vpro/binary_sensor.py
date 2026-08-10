"""Online binary sensor for vPro (AMT reachable)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VproEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VproOnlineSensor(coordinator)])


class VproOnlineSensor(VproEntity, BinarySensorEntity):
    """AMT firmware reachable (independent of OS power)."""

    _attr_name = "AMT online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def unique_id(self) -> str:
        return f"{self._host}_online"

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data.get(
            "power_state"
        ) is not None
