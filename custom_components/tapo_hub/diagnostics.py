# SPDX-License-Identifier: GPL-3.0-or-later
"""Diagnostics support for the Tapo Hub integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import format_mac

from .coordinator import TapoHubConfigEntry

TO_REDACT = {
    "username",
    "password",
    "credentials_hash",
    "unique_id",
    "alias",
    "mac",
    "host",
    "device_id",
    "ssid",
    "nickname",
    "ip",
    "latitude",
    "longitude",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TapoHubConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    device = coordinator.device
    oui = format_mac(device.mac)[:8].upper()
    return async_redact_data(
        {
            "entry_data": dict(entry.data),
            "oui": oui,
            "model": device.model,
            "device_last_response": device.internal_state,
            "children": [child.internal_state for child in device.children],
        },
        TO_REDACT,
    )
