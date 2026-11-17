# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests that write-path KasaExceptions surface as HomeAssistantError."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError
from kasa import Feature, KasaException
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tapo_hub.button import TapoHubButton
from custom_components.tapo_hub.const import DOMAIN
from custom_components.tapo_hub.coordinator import TapoHubCoordinator
from custom_components.tapo_hub.number import TapoHubNumber
from custom_components.tapo_hub.select import TapoHubSelect
from custom_components.tapo_hub.switch import TapoHubSwitch

from .kasa_fakes import make_hub_with_child


async def _failing_setter(*_args: object) -> None:
    raise KasaException("device offline")


async def _ok_setter(*_args: object) -> None:
    return None


def _build_coordinator(hass, hub):
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id=hub.device_id)
    entry.add_to_hass(hass)
    return TapoHubCoordinator(hass, hub, entry, timedelta(seconds=30))


async def test_switch_turn_on_failure_raises_translatable_error(hass):
    """A KasaException from set_value surfaces as HomeAssistantError.

    The coordinator must still be refreshed so the displayed state is
    reconciled with the device after a failed write.
    """
    hub = make_hub_with_child()
    coordinator = _build_coordinator(hass, hub)
    feature = Feature(
        device=hub,
        id="led",
        name="LED",
        type=Feature.Type.Switch,
        attribute_getter=lambda: True,
        attribute_setter=_failing_setter,
    )
    entity = TapoHubSwitch(coordinator, hub, feature)

    with (
        patch.object(coordinator, "async_request_refresh", AsyncMock()) as refresh,
        pytest.raises(HomeAssistantError) as exc_info,
    ):
        await entity.async_turn_on()

    refresh.assert_awaited_once()
    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key == "set_feature_value_failed"
    assert exc_info.value.translation_placeholders == {
        "feature": "LED",
        "error": "device offline",
    }
    assert isinstance(exc_info.value.__cause__, KasaException)


async def test_switch_turn_on_success_still_refreshes(hass):
    """The existing success path (refresh after a successful write) is unchanged."""
    hub = make_hub_with_child()
    coordinator = _build_coordinator(hass, hub)
    feature = Feature(
        device=hub,
        id="led",
        name="LED",
        type=Feature.Type.Switch,
        attribute_getter=lambda: True,
        attribute_setter=_ok_setter,
    )
    entity = TapoHubSwitch(coordinator, hub, feature)

    with patch.object(coordinator, "async_request_refresh", AsyncMock()) as refresh:
        await entity.async_turn_on()

    refresh.assert_awaited_once()


async def test_number_set_native_value_failure_raises_home_assistant_error(hass):
    """number.py's write path wraps KasaException the same way as switch.py."""
    hub = make_hub_with_child()
    coordinator = _build_coordinator(hass, hub)
    feature = Feature(
        device=hub,
        id="report_interval",
        name="Report interval",
        type=Feature.Type.Number,
        attribute_getter=lambda: 15,
        attribute_setter=_failing_setter,
        range_getter=lambda: (1, 60),
    )
    entity = TapoHubNumber(coordinator, hub, feature)

    with (
        patch.object(coordinator, "async_request_refresh", AsyncMock()) as refresh,
        pytest.raises(HomeAssistantError),
    ):
        await entity.async_set_native_value(30)

    refresh.assert_awaited_once()


async def test_button_press_failure_raises_home_assistant_error(hass):
    """button.py's write path wraps KasaException and now also refreshes."""
    hub = make_hub_with_child()
    coordinator = _build_coordinator(hass, hub)
    feature = Feature(
        device=hub,
        id="reboot",
        name="Reboot",
        type=Feature.Type.Action,
        attribute_setter=_failing_setter,
    )
    entity = TapoHubButton(coordinator, hub, feature)

    with (
        patch.object(coordinator, "async_request_refresh", AsyncMock()) as refresh,
        pytest.raises(HomeAssistantError),
    ):
        await entity.async_press()

    refresh.assert_awaited_once()


async def test_select_option_failure_raises_home_assistant_error(hass):
    """select.py has the identical set_value pattern and gets the same fix."""
    hub = make_hub_with_child()
    coordinator = _build_coordinator(hass, hub)
    feature = Feature(
        device=hub,
        id="mode",
        name="Mode",
        type=Feature.Type.Choice,
        attribute_getter=lambda: "a",
        attribute_setter=_failing_setter,
        choices_getter=lambda: ["a", "b"],
    )
    entity = TapoHubSelect(coordinator, hub, feature)

    with (
        patch.object(coordinator, "async_request_refresh", AsyncMock()) as refresh,
        pytest.raises(HomeAssistantError),
    ):
        await entity.async_select_option("b")

    refresh.assert_awaited_once()
