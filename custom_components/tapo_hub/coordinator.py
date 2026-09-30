# SPDX-License-Identifier: GPL-3.0-or-later
"""Data update coordinator for a Tapo Hub and its child devices."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from kasa import AuthenticationError, Device, KasaException

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

type TapoHubConfigEntry = ConfigEntry[TapoHubCoordinator]


class TapoHubCoordinator(DataUpdateCoordinator[None]):
    """Polls the hub (and transitively its children) for updated state."""

    config_entry: TapoHubConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        device: Device,
        config_entry: TapoHubConfigEntry,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=device.host,
            update_interval=update_interval,
        )
        self.device = device
        self._known_child_ids = {child.device_id for child in device.children}
        self.removed_child_ids: set[str] = set()

    async def _async_update_data(self) -> None:
        """Fetch fresh state for the hub and its children."""
        try:
            await self.device.update()
        except AuthenticationError as ex:
            raise ConfigEntryAuthFailed(f"Authentication failed: {ex}") from ex
        except KasaException as ex:
            raise UpdateFailed(f"Error communicating with hub: {ex}") from ex

        self._process_child_devices()

    def _process_child_devices(self) -> None:
        """Detect children that disappeared and remove their HA devices."""
        current_ids = {child.device_id for child in self.device.children}
        removed_ids = self._known_child_ids - current_ids
        if removed_ids:
            device_registry = dr.async_get(self.hass)
            for device_id in removed_ids:
                entry = device_registry.async_get_device(
                    identifiers={(DOMAIN, device_id)}
                )
                if entry is not None:
                    device_registry.async_update_device(
                        entry.id, remove_config_entry_id=self.config_entry.entry_id
                    )
        self.removed_child_ids = removed_ids
        self._known_child_ids = current_ids
