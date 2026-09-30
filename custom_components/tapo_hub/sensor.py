# SPDX-License-Identifier: GPL-3.0-or-later
"""Sensor platform for the Tapo Hub integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from kasa import Feature

from .coordinator import TapoHubConfigEntry
from .entity import TapoFeatureEntity, iter_feature_entities

# Coordinator centralizes the updates; no per-entity polling needed.
PARALLEL_UPDATES = 0

_DEVICE_CLASSES: dict[str, SensorDeviceClass] = {
    "temperature": SensorDeviceClass.TEMPERATURE,
    "humidity": SensorDeviceClass.HUMIDITY,
    "rssi": SensorDeviceClass.SIGNAL_STRENGTH,
    "battery_level": SensorDeviceClass.BATTERY,
    "device_time": SensorDeviceClass.TIMESTAMP,
    "on_since": SensorDeviceClass.TIMESTAMP,
}

_STATE_CLASSES: dict[str, SensorStateClass] = {
    "temperature": SensorStateClass.MEASUREMENT,
    "humidity": SensorStateClass.MEASUREMENT,
    "rssi": SensorStateClass.MEASUREMENT,
    "battery_level": SensorStateClass.MEASUREMENT,
}

_UNIT_MAPPING = {
    "celsius": UnitOfTemperature.CELSIUS,
    "fahrenheit": UnitOfTemperature.FAHRENHEIT,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TapoHubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for the hub and its children."""
    coordinator = entry.runtime_data
    known_unique_ids: set[str] = set()

    @callback
    def _check_devices() -> None:
        if entities := iter_feature_entities(
            coordinator,
            Feature.Type.Sensor,
            TapoHubSensor,
            known_unique_ids=known_unique_ids,
        ):
            async_add_entities(entities)

    _check_devices()
    entry.async_on_unload(coordinator.async_add_listener(_check_devices))


class TapoHubSensor(TapoFeatureEntity, SensorEntity):
    """A sensor entity backed by a read-only python-kasa feature."""

    @callback
    def _async_update_attrs(self) -> None:
        """Update the sensor's value from the feature."""
        value = self._feature.value
        if value is not None and self._feature.precision_hint is not None:
            value = round(value, self._feature.precision_hint)
            self._attr_suggested_display_precision = self._feature.precision_hint

        self._attr_native_value: str | int | float | datetime | None = value

        if (unit := self._feature.unit) is not None:
            self._attr_native_unit_of_measurement = _UNIT_MAPPING.get(unit, unit)

        if device_class := _DEVICE_CLASSES.get(self._feature.id):
            self._attr_device_class = device_class
        if state_class := _STATE_CLASSES.get(self._feature.id):
            self._attr_state_class = state_class
