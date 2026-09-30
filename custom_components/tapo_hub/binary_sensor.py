# SPDX-License-Identifier: GPL-3.0-or-later
"""Binary sensor platform for the Tapo Hub integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from kasa import Feature

from .coordinator import TapoHubConfigEntry
from .entity import TapoFeatureEntity, iter_feature_entities

PARALLEL_UPDATES = 0

_DEVICE_CLASSES: dict[str, BinarySensorDeviceClass] = {
    "battery_low": BinarySensorDeviceClass.BATTERY,
    "cloud_connection": BinarySensorDeviceClass.CONNECTIVITY,
    "overheated": BinarySensorDeviceClass.PROBLEM,
    "is_open": BinarySensorDeviceClass.DOOR,
    "motion_detected": BinarySensorDeviceClass.MOTION,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapoHubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors for the hub and its children."""
    coordinator = entry.runtime_data
    known_unique_ids: set[str] = set()

    @callback
    def _check_devices() -> None:
        if entities := iter_feature_entities(
            coordinator,
            Feature.Type.BinarySensor,
            TapoHubBinarySensor,
            known_unique_ids=known_unique_ids,
        ):
            async_add_entities(entities)

    _check_devices()
    entry.async_on_unload(coordinator.async_add_listener(_check_devices))


class TapoHubBinarySensor(TapoFeatureEntity, BinarySensorEntity):
    """A binary sensor entity backed by a read-only python-kasa feature."""

    @callback
    def _async_update_attrs(self) -> None:
        """Update the binary sensor's state from the feature."""
        self._attr_is_on = self._feature.value
        if device_class := _DEVICE_CLASSES.get(self._feature.id):
            self._attr_device_class = device_class
