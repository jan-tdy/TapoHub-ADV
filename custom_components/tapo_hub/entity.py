# SPDX-License-Identifier: GPL-3.0-or-later
#
# Portions of the entity/device-registry linking pattern in this file are
# adapted from Home Assistant's built-in "tplink" integration
# (homeassistant/components/tplink), licensed under the Apache License 2.0:
# https://github.com/home-assistant/core/blob/dev/LICENSE.md
"""Common entity base classes for the Tapo Hub integration.

Entities are generated generically from ``device.features`` so that new
features exposed by python-kasa show up automatically without needing a
per-device-model mapping.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from kasa import Device, Feature

from .const import DOMAIN, MANUFACTURER
from .coordinator import TapoHubCoordinator

_LOGGER = logging.getLogger(__name__)

_FEATURE_CATEGORY_TO_ENTITY_CATEGORY = {
    Feature.Category.Config: EntityCategory.CONFIG,
    Feature.Category.Info: EntityCategory.DIAGNOSTIC,
    Feature.Category.Debug: EntityCategory.DIAGNOSTIC,
}


class TapoFeatureEntity(CoordinatorEntity[TapoHubCoordinator], ABC):
    """Base class for an entity backed by a single python-kasa Feature."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TapoHubCoordinator,
        device: Device,
        feature: Feature,
        *,
        parent: Device | None = None,
        description: EntityDescription | None = None,
    ) -> None:
        """Initialize the feature entity."""
        super().__init__(coordinator)
        self._device = device
        self._feature = feature
        self._parent = parent

        self.entity_description = description or EntityDescription(
            key=feature.id,
            translation_key=feature.id,
            entity_category=_entity_category_for_feature(feature),
        )
        self._attr_unique_id = f"{device.device_id}_{feature.id}"
        self._attr_device_info = _device_info(device, parent=parent)

    @property
    def available(self) -> bool:
        """Return True if the coordinator and the underlying feature are healthy."""
        return self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        """Refresh entity state from the latest feature value."""
        self._async_update_attrs()
        super()._handle_coordinator_update()

    @abstractmethod
    @callback
    def _async_update_attrs(self) -> None:
        """Update entity attributes from the current feature value."""

    async def async_added_to_hass(self) -> None:
        """Populate initial state once added to hass."""
        await super().async_added_to_hass()
        self._async_update_attrs()


def _entity_category_for_feature(feature: Feature) -> EntityCategory | None:
    """Map a python-kasa feature category to a Home Assistant entity category."""
    if feature.category is Feature.Category.Primary:
        return None
    return _FEATURE_CATEGORY_TO_ENTITY_CATEGORY.get(
        feature.category, EntityCategory.DIAGNOSTIC
    )


def _device_info(device: Device, *, parent: Device | None = None) -> DeviceInfo:
    """Build the HA device registry entry for a hub or one of its children."""
    info = DeviceInfo(
        identifiers={(DOMAIN, device.device_id)},
        manufacturer=MANUFACTURER,
        model=device.model,
        name=device.alias or device.model,
        sw_version=device.hw_info.get("sw_ver"),
        hw_version=device.hw_info.get("hw_ver"),
    )
    if parent is not None:
        info["via_device"] = (DOMAIN, parent.device_id)
    else:
        info["connections"] = {(dr.CONNECTION_NETWORK_MAC, device.mac)}
    return info


def iter_feature_entities(
    coordinator: TapoHubCoordinator,
    feature_type: Feature.Type,
    entity_class: type[Any],
    *,
    known_unique_ids: set[str],
) -> list[Any]:
    """Build entities for every not-yet-seen feature of the given type.

    Walks the hub device and all of its currently known children.
    """
    entities: list[Any] = []
    devices: list[tuple[Device, Device | None]] = [(coordinator.device, None)]
    devices.extend((child, coordinator.device) for child in coordinator.device.children)

    for device, parent in devices:
        for feature in device.features.values():
            if feature.type is not feature_type:
                continue
            unique_id = f"{device.device_id}_{feature.id}"
            if unique_id in known_unique_ids:
                continue
            known_unique_ids.add(unique_id)
            entities.append(
                entity_class(coordinator, device, feature, parent=parent)
            )
    return entities
