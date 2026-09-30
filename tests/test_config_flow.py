# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the Tapo Hub config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from kasa import AuthenticationError, KasaException

from custom_components.tapo_hub.const import CONF_CONNECTION_PARAMETERS, DOMAIN

from .kasa_fakes import make_hub_with_child


async def test_user_flow_success(hass):
    """Entering a host + valid credentials creates a config entry."""
    hub = make_hub_with_child()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.tapo_hub.config_flow.Discover.discover_single",
        AsyncMock(return_value=hub),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: hub.host,
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "hunter2",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == hub.alias
    assert result["data"][CONF_HOST] == hub.host
    assert result["data"][CONF_CONNECTION_PARAMETERS]
    await hass.async_block_till_done()


async def test_user_flow_invalid_auth(hass):
    """An AuthenticationError from discovery surfaces as invalid_auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.tapo_hub.config_flow.Discover.discover_single",
        AsyncMock(side_effect=AuthenticationError("bad credentials")),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.50",
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "wrong",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass):
    """A KasaException from discovery surfaces as cannot_connect."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.tapo_hub.config_flow.Discover.discover_single",
        AsyncMock(side_effect=KasaException("unreachable")),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "192.168.1.50",
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "hunter2",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_rejects_non_hub_device(hass):
    """Connecting successfully to a non-hub device is rejected."""
    from kasa import DeviceType  # noqa: PLC0415

    hub = make_hub_with_child()
    hub.device_type = DeviceType.Plug

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.tapo_hub.config_flow.Discover.discover_single",
        AsyncMock(return_value=hub),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: hub.host,
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "hunter2",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "not_a_hub"}
