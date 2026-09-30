# SPDX-License-Identifier: GPL-3.0-or-later
"""Config flow for the Tapo Hub integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from kasa import (
    AuthenticationError,
    Credentials,
    Device,
    DeviceConfig,
    Discover,
    KasaException,
)
from kasa import (
    TimeoutError as KasaTimeoutError,
)

from .const import (
    CONF_CONNECTION_PARAMETERS,
    CONF_CREDENTIALS_HASH,
    CONF_SCAN_INTERVAL,
    CONNECT_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DISCOVERY_TIMEOUT,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_HOST, default=""): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_RECONFIGURE_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


class TapoHubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tapo Hub."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return TapoHubOptionsFlow()

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._credentials: Credentials | None = None
        self._discovered: dict[str, Device] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: host + TP-Link account credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            credentials = Credentials(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            host = user_input[CONF_HOST].strip()

            if not host:
                return await self._async_start_discovery(credentials)

            self._async_abort_entries_match({CONF_HOST: host})
            try:
                device = await Discover.discover_single(
                    host,
                    credentials=credentials,
                    discovery_timeout=DISCOVERY_TIMEOUT,
                    timeout=CONNECT_TIMEOUT,
                )
                await device.update()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except (KasaException, KasaTimeoutError):
                errors["base"] = "cannot_connect"
            else:
                if device.device_type is not Device.Type.Hub:
                    errors["base"] = "not_a_hub"
                else:
                    return await self._async_create_entry(device, credentials)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def _async_start_discovery(
        self, credentials: Credentials
    ) -> ConfigFlowResult:
        """Broadcast-discover hubs on the LAN and let the user pick one."""
        found = await Discover.discover(
            credentials=credentials,
            discovery_timeout=DISCOVERY_TIMEOUT,
            timeout=CONNECT_TIMEOUT,
        )
        configured_hosts = {
            entry.data[CONF_HOST] for entry in self._async_current_entries()
        }
        self._discovered = {
            ip: device
            for ip, device in found.items()
            if device.device_type is Device.Type.Hub and ip not in configured_hosts
        }
        self._credentials = credentials

        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        return await self.async_step_pick_device()

    async def async_step_pick_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user choose among broadcast-discovered hubs."""
        if user_input is not None:
            device = self._discovered[user_input[CONF_HOST]]
            assert self._credentials is not None
            try:
                await device.update()
            except (AuthenticationError, KasaException):
                return self.async_abort(reason="cannot_connect")
            return await self._async_create_entry(device, self._credentials)

        choices = {
            ip: f"{device.alias or device.model} ({ip})"
            for ip, device in self._discovered.items()
        }
        return self.async_show_form(
            step_id="pick_device",
            data_schema=vol.Schema({vol.Required(CONF_HOST): vol.In(choices)}),
        )

    async def _async_create_entry(
        self, device: Device, credentials: Credentials
    ) -> ConfigFlowResult:
        """Create the config entry from a live, authenticated hub device."""
        # device_id is stable across IP changes, unlike the host.
        await self.async_set_unique_id(device.device_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: device.host})

        data: dict[str, Any] = {
            CONF_HOST: device.host,
            CONF_USERNAME: credentials.username,
            CONF_PASSWORD: credentials.password,
            CONF_CONNECTION_PARAMETERS: device.config.connection_type.to_dict(),
        }
        if device.credentials_hash:
            data[CONF_CREDENTIALS_HASH] = device.credentials_hash

        return self.async_create_entry(
            title=device.alias or device.model, data=data
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Start the reauth flow when stored credentials stop working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for fresh TP-Link account credentials."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            credentials = Credentials(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            config = DeviceConfig(
                reauth_entry.data[CONF_HOST],
                credentials=credentials,
                timeout=CONNECT_TIMEOUT,
            )
            if conn_params := reauth_entry.data.get(CONF_CONNECTION_PARAMETERS):
                config.connection_type = Device.ConnectionParameters.from_dict(
                    conn_params
                )
            try:
                device = await Device.connect(config=config)
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except (KasaException, KasaTimeoutError):
                errors["base"] = "cannot_connect"
            else:
                updates: dict[str, Any] = {
                    CONF_USERNAME: credentials.username,
                    CONF_PASSWORD: credentials.password,
                }
                if device.credentials_hash:
                    updates[CONF_CREDENTIALS_HASH] = device.credentials_hash
                return self.async_update_reload_and_abort(
                    reauth_entry, data={**reauth_entry.data, **updates}
                )

        return self.async_show_form(
            step_id="reauth_confirm", data_schema=STEP_AUTH_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow changing the hub's IP address after a DHCP lease change."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            credentials = Credentials(
                reconfigure_entry.data[CONF_USERNAME],
                reconfigure_entry.data[CONF_PASSWORD],
            )
            try:
                device = await Discover.discover_single(
                    host,
                    credentials=credentials,
                    discovery_timeout=DISCOVERY_TIMEOUT,
                    timeout=CONNECT_TIMEOUT,
                )
                await device.update()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except (KasaException, KasaTimeoutError):
                errors["base"] = "cannot_connect"
            else:
                if device.device_id != reconfigure_entry.unique_id:
                    errors["base"] = "unexpected_device"
                else:
                    return self.async_update_reload_and_abort(
                        reconfigure_entry,
                        data={
                            **reconfigure_entry.data,
                            CONF_HOST: device.host,
                            CONF_CONNECTION_PARAMETERS: (
                                device.config.connection_type.to_dict()
                            ),
                        },
                    )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_RECONFIGURE_SCHEMA,
                {CONF_HOST: reconfigure_entry.data[CONF_HOST]},
            ),
            errors=errors,
        )


class TapoHubOptionsFlow(OptionsFlow):
    """Handle options for a Tapo Hub config entry (currently just polling interval)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the polling interval option."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
