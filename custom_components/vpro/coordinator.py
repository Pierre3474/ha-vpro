"""Data update coordinator for vPro / AMT."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .amt import AMTClient, AMTError
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class VproCoordinator(DataUpdateCoordinator):
    """Polls AMT power state (and versions once)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: AMTClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"vpro {entry.data['host']}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.entry = entry
        self._versions: dict[str, str] | None = None

    async def _async_update_data(self) -> dict:
        try:
            state = await self.hass.async_add_executor_job(self.client.get_power_state)
            if self._versions is None:
                try:
                    self._versions = await self.hass.async_add_executor_job(
                        self.client.get_versions
                    )
                except AMTError:
                    self._versions = {}
        except AMTError as err:
            raise UpdateFailed(str(err)) from err
        return {"power_state": state, "versions": self._versions or {}}
