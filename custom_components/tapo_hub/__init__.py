# SPDX-License-Identifier: GPL-3.0-or-later
"""The Tapo Hub integration.

Connects to a TP-Link/Tapo H100 hub (and its paired T310/T315/S200B
child devices) over the local network using the TPAP protocol, which is
only supported by an unreleased python-kasa branch. See README.md for
why the upstream ``tplink`` integration does not work with this hub.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from kasa import AuthenticationError, Credentials, Device, DeviceConfig, KasaException

from .const import (
    CONF_CONNECTION_PARAMETERS,
    CONF_CREDENTIALS_HASH,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MANUFACTURER,
    PLATFORMS,
)
from .coordinator import TapoHubConfigEntry, TapoHubCoordinator

_LOGGER = logging.getLogger(__name__)


async def _async_connect(hass: HomeAssistant, entry: ConfigEntry) -> Device:
    """Build a DeviceConfig from stored entry data and connect to the hub."""
    config = DeviceConfig(entry.data[CONF_HOST], timeout=10)

    if conn_params_dict := entry.data.get(CONF_CONNECTION_PARAMETERS):
        config.connection_type = Device.ConnectionParameters.from_dict(
            conn_params_dict
        )

    if credentials_hash := entry.data.get(CONF_CREDENTIALS_HASH):
        config.credentials_hash = credentials_hash
    else:
        config.credentials = Credentials(
            entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
        )

    try:
        device = await Device.connect(config=config)
    except AuthenticationError as ex:
        if credentials_hash and CONF_USERNAME in entry.data:
            # The stored hash may have expired; retry once with the
            # full credentials before giving up.
            config.credentials_hash = None
            config.credentials = Credentials(
                entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
            )
            try:
                device = await Device.connect(config=config)
            except AuthenticationError as retry_ex:
                raise ConfigEntryAuthFailed(str(retry_ex)) from retry_ex
        else:
            raise ConfigEntryAuthFailed(str(ex)) from ex
    except KasaException as ex:
        raise ConfigEntryNotReady(f"Unable to connect to {entry.data[CONF_HOST]}: {ex}") from ex

    return device


async def async_setup_entry(hass: HomeAssistant, entry: TapoHubConfigEntry) -> bool:
    """Set up Tapo Hub from a config entry."""
    device = await _async_connect(hass, entry)

    if device.credentials_hash and device.credentials_hash != entry.data.get(
        CONF_CREDENTIALS_HASH
    ):
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_CREDENTIALS_HASH: device.credentials_hash}
        )

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = TapoHubCoordinator(
        hass, device, entry, timedelta(seconds=scan_interval)
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Register the hub device before forwarding platforms so that child
    # device entities can resolve their via_device link.
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, device.device_id)},
        manufacturer=MANUFACTURER,
        model=device.model,
        name=device.alias or device.model,
        sw_version=device.hw_info.get("sw_ver"),
        hw_version=device.hw_info.get("hw_ver"),
        connections={(dr.CONNECTION_NETWORK_MAC, device.mac)},
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: TapoHubConfigEntry) -> None:
    """Reload the entry when its options change (e.g. scan interval)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: TapoHubConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.device.disconnect()
    return unload_ok
