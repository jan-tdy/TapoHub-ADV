# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for generic feature-to-entity generation."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from kasa import Feature
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tapo_hub.const import DOMAIN
from custom_components.tapo_hub.coordinator import TapoHubCoordinator
from custom_components.tapo_hub.entity import iter_feature_entities
from custom_components.tapo_hub.sensor import TapoHubSensor

from .kasa_fakes import make_hub_with_child


async def test_iter_feature_entities_covers_hub_and_child(hass):
    """Sensor features on both the hub and its child are discovered."""
    hub = make_hub_with_child()
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=hub.device_id)
    entry.add_to_hass(hass)
    coordinator = TapoHubCoordinator(hass, hub, entry, timedelta(seconds=30))

    known: set[str] = set()
    entities = iter_feature_entities(
        coordinator, Feature.Type.Sensor, TapoHubSensor, known_unique_ids=known
    )

    unique_ids = {e.unique_id for e in entities}
    assert f"{hub.device_id}_rssi" in unique_ids
    assert f"{hub.children[0].device_id}_temperature" in unique_ids
    assert f"{hub.children[0].device_id}_humidity" in unique_ids

    # Calling again with the same known set yields no duplicates.
    assert iter_feature_entities(
        coordinator, Feature.Type.Sensor, TapoHubSensor, known_unique_ids=known
    ) == []


async def test_removed_then_repaired_child_entities_are_recreated(hass):
    """A child removed and later re-paired gets its entities recreated.

    Regression test for entities never reappearing because their unique IDs
    stayed in ``known_unique_ids`` forever, even though the coordinator
    tracks the device as removed in ``removed_child_ids``.
    """
    hub = make_hub_with_child()
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=hub.device_id)
    entry.add_to_hass(hass)
    coordinator = TapoHubCoordinator(hass, hub, entry, timedelta(seconds=30))
    child = hub.children[0]

    known: set[str] = set()
    iter_feature_entities(
        coordinator, Feature.Type.Sensor, TapoHubSensor, known_unique_ids=known
    )
    assert f"{child.device_id}_temperature" in known

    # Child disappears: the coordinator detects and reports the removal.
    hub.children = []
    await coordinator._async_update_data()
    assert coordinator.removed_child_ids == {child.device_id}

    # Child reappears (re-paired) before the next poll's removed_child_ids
    # has been reset to empty by a subsequent update.
    hub.children = [child]
    entities = iter_feature_entities(
        coordinator, Feature.Type.Sensor, TapoHubSensor, known_unique_ids=known
    )

    unique_ids = {e.unique_id for e in entities}
    assert f"{child.device_id}_temperature" in unique_ids
    assert f"{child.device_id}_humidity" in unique_ids


async def test_temperature_sensor_attributes(hass):
    """The temperature feature maps to the right device_class/state_class/unit."""
    hub = make_hub_with_child()
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=hub.device_id)
    entry.add_to_hass(hass)
    coordinator = TapoHubCoordinator(hass, hub, entry, timedelta(seconds=30))
    child = hub.children[0]
    feature = child.features["temperature"]

    entity = TapoHubSensor(coordinator, child, feature, parent=hub)
    entity._async_update_attrs()

    assert entity.native_value == 21.5
    assert entity.device_class is SensorDeviceClass.TEMPERATURE
    assert entity.state_class is SensorStateClass.MEASUREMENT
    assert entity.unique_id == f"{child.device_id}_temperature"


async def test_child_device_info_links_via_device(hass):
    """Child entities point their via_device at the hub's identifier."""
    hub = make_hub_with_child()
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=hub.device_id)
    entry.add_to_hass(hass)
    coordinator = TapoHubCoordinator(hass, hub, entry, timedelta(seconds=30))
    child = hub.children[0]
    feature = child.features["temperature"]

    entity = TapoHubSensor(coordinator, child, feature, parent=hub)

    assert entity.device_info["via_device"] == (DOMAIN, hub.device_id)
    assert entity.device_info["identifiers"] == {(DOMAIN, child.device_id)}
