# SPDX-License-Identifier: GPL-3.0-or-later
"""Button platform for the Tapo Hub integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from kasa import Feature

from .coordinator import TapoHubConfigEntry
from .entity import TapoFeatureEntity, iter_feature_entities

PARALLEL_UPDATES = 0

_DEVICE_CLASSES: dict[str, ButtonDeviceClass] = {
    "reboot": ButtonDeviceClass.RESTART,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapoHubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up buttons for the hub and its children."""
    coordinator = entry.runtime_data
    known_unique_ids: set[str] = set()

    @callback
    def _check_devices() -> None:
        if entities := iter_feature_entities(
            coordinator,
            Feature.Type.Action,
            TapoHubButton,
            known_unique_ids=known_unique_ids,
        ):
            async_add_entities(entities)

    _check_devices()
    entry.async_on_unload(coordinator.async_add_listener(_check_devices))


class TapoHubButton(TapoFeatureEntity, ButtonEntity):
    """A button entity backed by an action-type python-kasa feature."""

    @callback
    def _async_update_attrs(self) -> None:
        """Nothing to refresh for a stateless action."""
        if device_class := _DEVICE_CLASSES.get(self._feature.id):
            self._attr_device_class = device_class

    async def async_press(self) -> None:
        """Trigger the feature's action."""
        await self._feature.set_value(True)
