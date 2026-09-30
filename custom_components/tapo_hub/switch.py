# SPDX-License-Identifier: GPL-3.0-or-later
"""Switch platform for the Tapo Hub integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from kasa import Feature

from .coordinator import TapoHubConfigEntry
from .entity import TapoFeatureEntity, iter_feature_entities

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapoHubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches for the hub and its children."""
    coordinator = entry.runtime_data
    known_unique_ids: set[str] = set()

    @callback
    def _check_devices() -> None:
        if entities := iter_feature_entities(
            coordinator,
            Feature.Type.Switch,
            TapoHubSwitch,
            known_unique_ids=known_unique_ids,
        ):
            async_add_entities(entities)

    _check_devices()
    entry.async_on_unload(coordinator.async_add_listener(_check_devices))


class TapoHubSwitch(TapoFeatureEntity, SwitchEntity):
    """A switch entity backed by a boolean, settable python-kasa feature."""

    @callback
    def _async_update_attrs(self) -> None:
        """Update the switch's state from the feature."""
        self._attr_is_on = self._feature.value

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the feature on."""
        await self._feature.set_value(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the feature off."""
        await self._feature.set_value(False)
        await self.coordinator.async_request_refresh()
