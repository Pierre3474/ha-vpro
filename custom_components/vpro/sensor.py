"""Sensors for vPro (power state, AMT version)."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import amt
from .const import DOMAIN
from .entity import VproEntity

_STATE_NAMES = {
    amt.POWER_ON: "on",
    amt.POWER_SLEEP_LIGHT: "sleep",
    amt.POWER_SLEEP_DEEP: "sleep",
    amt.POWER_HIBERNATE: "hibernate",
    6: "off",
    8: "off",
    12: "off",
    13: "off",
    14: "off",
    15: "off",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VproPowerStateSensor(coordinator), VproAmtVersionSensor(coordinator)])


class VproPowerStateSensor(VproEntity, SensorEntity):
    _attr_name = "Power state"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["on", "off", "sleep", "hibernate", "unknown"]
    _attr_icon = "mdi:power-settings"

    @property
    def unique_id(self) -> str:
        return f"{self._host}_power_state"

    @property
    def native_value(self) -> str:
        state = self.coordinator.data.get("power_state")
        return _STATE_NAMES.get(state, "unknown")

    @property
    def extra_state_attributes(self) -> dict:
        return {"cim_power_state": self.coordinator.data.get("power_state")}


class VproAmtVersionSensor(VproEntity, SensorEntity):
    _attr_name = "AMT version"
    _attr_icon = "mdi:chip"
    _attr_entity_registry_enabled_default = True

    @property
    def unique_id(self) -> str:
        return f"{self._host}_amt_version"

    @property
    def native_value(self) -> str | None:
        versions = self.coordinator.data.get("versions", {})
        return versions.get("AMT") or versions.get("Flash") or next(iter(versions.values()), None)

    @property
    def extra_state_attributes(self) -> dict:
        return dict(self.coordinator.data.get("versions", {}))
