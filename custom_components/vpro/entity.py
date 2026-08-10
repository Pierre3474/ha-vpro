"""Shared base entity for vPro."""
from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_info import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VproCoordinator


class VproEntity(CoordinatorEntity[VproCoordinator]):
    """Base entity tying entities to one vPro device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VproCoordinator) -> None:
        super().__init__(coordinator)
        host = coordinator.entry.data[CONF_HOST]
        self._host = host
        versions = coordinator.data.get("versions", {}) if coordinator.data else {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host)},
            name=coordinator.entry.title,
            manufacturer="Intel",
            model="vPro / AMT",
            sw_version=versions.get("AMT") or versions.get("Flash"),
            configuration_url=f"https://{host}:16993",
        )
