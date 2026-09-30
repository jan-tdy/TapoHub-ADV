# SPDX-License-Identifier: GPL-3.0-or-later
"""Lightweight fakes standing in for real python-kasa Device objects in tests.

Real `kasa.Feature` instances are used (it is a plain dataclass with no
`isinstance` checks on its `device`/`container` field), so feature `.value`
and `.set_value()` behave exactly as they would against a real device —
only the `Device` they read from/write to is a duck-typed fake.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock

from kasa import (
    Credentials,
    DeviceConfig,
    DeviceConnectionParameters,
    DeviceEncryptionType,
    DeviceFamily,
    DeviceType,
    Feature,
)


@dataclass
class FakeDevice:
    """Duck-typed stand-in for kasa.Device used by our integration code.

    Only implements the attributes our integration actually reads; it does
    not subclass kasa.Device (which is an ABC with many abstract members we
    do not need for these tests).
    """

    device_id: str
    model: str
    alias: str
    host: str
    mac: str
    device_type: DeviceType = DeviceType.Hub
    temperature: float | None = None
    humidity: int | None = None
    battery_low: bool | None = None
    rssi: int | None = None
    report_interval: int = 15
    parent: FakeDevice | None = None
    children: list[FakeDevice] = field(default_factory=list)
    credentials_hash: str | None = "fake-hash"

    def __post_init__(self) -> None:
        self.hw_info = {"sw_ver": "1.0.0", "hw_ver": "1.0"}
        self.config = DeviceConfig(
            host=self.host,
            credentials=Credentials("user@example.com", "hunter2"),
            connection_type=DeviceConnectionParameters(
                device_family=DeviceFamily.SmartTapoHub,
                encryption_type=DeviceEncryptionType.Tpap,
            ),
        )
        self.internal_state: dict[str, Any] = {"device_id": self.device_id}
        self._features: dict[str, Feature] = {}
        self.update = AsyncMock()
        self.disconnect = AsyncMock()

        if self.temperature is not None:
            self._add_feature(
                Feature(
                    device=self,
                    id="temperature",
                    name="Temperature",
                    type=Feature.Type.Sensor,
                    attribute_getter="temperature",
                    unit_getter=lambda: "celsius",
                    precision_hint=1,
                )
            )
        if self.humidity is not None:
            self._add_feature(
                Feature(
                    device=self,
                    id="humidity",
                    name="Humidity",
                    type=Feature.Type.Sensor,
                    attribute_getter="humidity",
                    unit_getter=lambda: "%",
                )
            )
        if self.battery_low is not None:
            self._add_feature(
                Feature(
                    device=self,
                    id="battery_low",
                    name="Battery low",
                    type=Feature.Type.BinarySensor,
                    attribute_getter="battery_low",
                )
            )
        if self.rssi is not None:
            self._add_feature(
                Feature(
                    device=self,
                    id="rssi",
                    name="RSSI",
                    type=Feature.Type.Sensor,
                    attribute_getter="rssi",
                    category=Feature.Category.Debug,
                )
            )
        self._add_feature(
            Feature(
                device=self,
                id="report_interval",
                name="Report interval",
                type=Feature.Type.Number,
                attribute_getter="report_interval",
                attribute_setter="_set_report_interval",
                range_getter=lambda: (1, 60),
                category=Feature.Category.Config,
            )
        )

    def _add_feature(self, feature: Feature) -> None:
        self._features[feature.id] = feature

    @property
    def features(self) -> dict[str, Feature]:
        return self._features

    async def _set_report_interval(self, value: int) -> None:
        self.report_interval = value


def make_hub_with_child() -> FakeDevice:
    """Build a fake H100 hub with one fake T310 child, like the real pairing."""
    hub = FakeDevice(
        device_id="HUB000000000000000000000000000000000001",
        model="H100",
        alias="Tapo Hub",
        host="192.168.1.50",
        mac="AA:BB:CC:00:00:01",
        device_type=DeviceType.Hub,
        rssi=-45,
    )
    child = FakeDevice(
        device_id="T310000000000000000000000000000000000001",
        model="T310",
        alias="Living Room Sensor",
        host=hub.host,
        mac="AA:BB:CC:00:00:02",
        device_type=DeviceType.Sensor,
        temperature=21.5,
        humidity=47,
        battery_low=False,
        parent=hub,
    )
    hub.children = [child]
    return hub
