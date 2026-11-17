# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the Tapo Hub setup/connect flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from kasa import AuthenticationError, KasaException
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tapo_hub import _async_connect
from custom_components.tapo_hub.const import CONF_CREDENTIALS_HASH, DOMAIN


async def test_connect_expired_hash_retries_with_credentials(hass):
    """An expired credentials hash is retried with the stored username/password."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "10.0.0.5",
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "secret",
            CONF_CREDENTIALS_HASH: "stale-hash",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.tapo_hub.Device.connect",
        AsyncMock(side_effect=[AuthenticationError("expired"), object()]),
    ):
        device = await _async_connect(hass, entry)

    assert device is not None


async def test_connect_expired_hash_retry_auth_failure(hass):
    """If the retry with full credentials also fails auth, raise ConfigEntryAuthFailed."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "10.0.0.5",
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "wrong",
            CONF_CREDENTIALS_HASH: "stale-hash",
        },
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.tapo_hub.Device.connect",
            AsyncMock(
                side_effect=[
                    AuthenticationError("expired"),
                    AuthenticationError("bad credentials"),
                ]
            ),
        ),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await _async_connect(hass, entry)


async def test_connect_expired_hash_retry_kasa_exception(hass):
    """A non-auth KasaException on the credentials retry surfaces as ConfigEntryNotReady.

    Regression test: the retry branch used to only catch AuthenticationError,
    so a transient network failure on retry (e.g. a timeout) escaped
    _async_connect as a raw KasaException instead of ConfigEntryNotReady.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "10.0.0.5",
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "secret",
            CONF_CREDENTIALS_HASH: "stale-hash",
        },
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.tapo_hub.Device.connect",
            AsyncMock(
                side_effect=[
                    AuthenticationError("expired"),
                    KasaException("network unreachable"),
                ]
            ),
        ),
        pytest.raises(ConfigEntryNotReady),
    ):
        await _async_connect(hass, entry)
