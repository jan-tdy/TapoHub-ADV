# SPDX-License-Identifier: GPL-3.0-or-later
"""Select platform for the Tapo Hub integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
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
    """Set up selects for the hub and its children."""
    coordinator = entry.runtime_data
    known_unique_ids: set[str] = set()

    @callback
    def _check_devices() -> None:
        if entities := iter_feature_entities(
            coordinator,
            Feature.Type.Choice,
            TapoHubSelect,
            known_unique_ids=known_unique_ids,
        ):
            async_add_entities(entities)

    _check_devices()
    entry.async_on_unload(coordinator.async_add_listener(_check_devices))


class TapoHubSelect(TapoFeatureEntity, SelectEntity):
    """A select entity backed by a choice-based, settable python-kasa feature."""

    _description_class = SelectEntityDescription

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the select with its options.

        SelectEntity requires options as soon as the entity is added, before
        async_added_to_hass() has called _async_update_attrs().
        """
        super().__init__(*args, **kwargs)
        self._attr_options = self._feature.choices or []

    @callback
    def _async_update_attrs(self) -> None:
        """Update the select's options and current value from the feature."""
        self._attr_options = self._feature.choices or []
        value = self._feature.value
        self._attr_current_option = value.name if hasattr(value, "name") else value

    async def async_select_option(self, option: str) -> None:
        """Set the feature's value."""
        await self._feature.set_value(option)
        await self.coordinator.async_request_refresh()
