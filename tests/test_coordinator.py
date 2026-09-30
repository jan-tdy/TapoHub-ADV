# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for TapoHubCoordinator."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from kasa import AuthenticationError, KasaException
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tapo_hub.const import DOMAIN
from custom_components.tapo_hub.coordinator import TapoHubCoordinator

from .kasa_fakes import make_hub_with_child


async def test_update_success(hass):
    """A successful update calls device.update() and leaves children intact."""
    hub = make_hub_with_child()
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=hub.device_id)
    entry.add_to_hass(hass)
    coordinator = TapoHubCoordinator(hass, hub, entry, timedelta(seconds=30))

    await coordinator._async_update_data()

    hub.update.assert_awaited_once()
    assert coordinator.removed_child_ids == set()


async def test_update_authentication_error(hass):
    """An AuthenticationError from the device surfaces as ConfigEntryAuthFailed."""
    hub = make_hub_with_child()
    hub.update.side_effect = AuthenticationError("bad credentials")
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=hub.device_id)
    entry.add_to_hass(hass)
    coordinator = TapoHubCoordinator(hass, hub, entry, timedelta(seconds=30))

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_update_kasa_exception(hass):
    """A generic KasaException surfaces as UpdateFailed."""
    hub = make_hub_with_child()
    hub.update.side_effect = KasaException("network unreachable")
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=hub.device_id)
    entry.add_to_hass(hass)
    coordinator = TapoHubCoordinator(hass, hub, entry, timedelta(seconds=30))

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_child_removal_detected(hass):
    """A child that disappears between polls is reported in removed_child_ids."""
    hub = make_hub_with_child()
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=hub.device_id)
    entry.add_to_hass(hass)
    coordinator = TapoHubCoordinator(hass, hub, entry, timedelta(seconds=30))

    removed_child_id = hub.children[0].device_id
    hub.children = []

    await coordinator._async_update_data()

    assert coordinator.removed_child_ids == {removed_child_id}
