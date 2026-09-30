# SPDX-License-Identifier: GPL-3.0-or-later
"""Number platform for the Tapo Hub integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
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
    """Set up numbers for the hub and its children."""
    coordinator = entry.runtime_data
    known_unique_ids: set[str] = set()

    @callback
    def _check_devices() -> None:
        if entities := iter_feature_entities(
            coordinator,
            Feature.Type.Number,
            TapoHubNumber,
            known_unique_ids=known_unique_ids,
        ):
            async_add_entities(entities)

    _check_devices()
    entry.async_on_unload(coordinator.async_add_listener(_check_devices))


class TapoHubNumber(TapoFeatureEntity, NumberEntity):
    """A number entity backed by a numeric, settable python-kasa feature."""

    _attr_mode = NumberMode.BOX

    @callback
    def _async_update_attrs(self) -> None:
        """Update the number's value and range from the feature."""
        self._attr_native_value = self._feature.value
        self._attr_native_min_value = self._feature.minimum_value
        self._attr_native_max_value = self._feature.maximum_value
        if (unit := self._feature.unit) is not None:
            self._attr_native_unit_of_measurement = unit

    async def async_set_native_value(self, value: float) -> None:
        """Set the feature's value."""
        await self._feature.set_value(value)
        await self.coordinator.async_request_refresh()
