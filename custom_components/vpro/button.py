"""Action buttons for vPro (reset, power cycle, boot to BIOS)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import amt
from .amt import AMTClient
from .const import DOMAIN
from .entity import VproEntity


@dataclass(frozen=True, kw_only=True)
class VproButtonDescription(ButtonEntityDescription):
    action: Callable[[AMTClient], object]


BUTTONS: tuple[VproButtonDescription, ...] = (
    VproButtonDescription(
        key="reset",
        name="Reset",
        icon="mdi:restart-alert",
        action=lambda c: c.set_power(amt.POWER_RESET),
    ),
    VproButtonDescription(
        key="power_cycle",
        name="Power cycle",
        icon="mdi:restart",
        action=lambda c: c.set_power(amt.POWER_CYCLE_SOFT),
    ),
    VproButtonDescription(
        key="boot_bios",
        name="Boot to BIOS",
        icon="mdi:chip",
        action=lambda c: c.boot_to_bios(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(VproButton(coordinator, desc) for desc in BUTTONS)


class VproButton(VproEntity, ButtonEntity):
    entity_description: VproButtonDescription

    def __init__(self, coordinator, description: VproButtonDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description

    @property
    def unique_id(self) -> str:
        return f"{self._host}_{self.entity_description.key}"

    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(
            self.entity_description.action, self.coordinator.client
        )
        await self.coordinator.async_request_refresh()
