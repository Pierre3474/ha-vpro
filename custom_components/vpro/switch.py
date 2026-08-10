"""Power switch for vPro."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import amt
from .const import DOMAIN
from .entity import VproEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VproPowerSwitch(coordinator)])


class VproPowerSwitch(VproEntity, SwitchEntity):
    """On = AMT power up (2), Off = AMT soft off (8)."""

    _attr_name = "Power"
    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_icon = "mdi:power"

    @property
    def unique_id(self) -> str:
        return f"{self._host}_power"

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data.get("power_state")
        if state is None:
            return None
        return state in amt.ON_STATES

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_power, amt.POWER_ON
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_power, amt.POWER_OFF_SOFT
        )
        await self.coordinator.async_request_refresh()
