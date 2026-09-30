# SPDX-License-Identifier: GPL-3.0-or-later
"""Constants for the Tapo Hub integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "tapo_hub"

MANUFACTURER: Final = "TP-Link"

#: Seconds to wait for UDP discovery responses.
DISCOVERY_TIMEOUT: Final = 5
#: Seconds to wait for a single device query.
CONNECT_TIMEOUT: Final = 10
#: Default seconds between coordinator polls.
DEFAULT_SCAN_INTERVAL: Final = 30
#: Minimum allowed scan interval, to avoid flooding the hub.
MIN_SCAN_INTERVAL: Final = 10

CONF_CONNECTION_PARAMETERS: Final = "connection_parameters"
CONF_CREDENTIALS_HASH: Final = "credentials_hash"
CONF_SCAN_INTERVAL: Final = "scan_interval"

PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]
