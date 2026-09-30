#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Manual smoke test for the pinned python-kasa TPAP fork against a real H100.

Connects to a Tapo H100 hub, runs discovery, calls update(), and prints the
hub's and its children's features. Useful for validating a candidate
python-kasa commit before pinning it in manifest.json.

Credentials are read from environment variables — never hardcode them here
and never commit them:

    TAPO_HOST=192.168.1.50 \\
    TAPO_USERNAME=you@example.com \\
    TAPO_PASSWORD='your-password' \\
    python scripts/smoke_test.py

Optional:
    TAPO_TIMEOUT       query timeout in seconds (default 10)
    TAPO_DISC_TIMEOUT  discovery timeout in seconds (default 5)
"""

from __future__ import annotations

import asyncio
import os
import sys


def _print_device_features(device) -> None:  # noqa: ANN001
    print(f"\n=== {device.alias or '(no alias)'} ({device.model}) ===")
    print(f"device_id: {device.device_id}")
    print(f"device_type: {device.device_type}")
    print(f"host: {device.host}")
    if not device.features:
        print("  (no features reported)")
        return
    for feature_id, feature in sorted(device.features.items()):
        try:
            value = feature.value
        except Exception as ex:  # noqa: BLE001
            value = f"<error reading value: {ex}>"
        unit = ""
        try:
            if feature.unit:
                unit = f" {feature.unit}"
        except Exception:  # noqa: BLE001, S110
            pass
        print(f"  {feature_id:30s} = {value}{unit}")


async def main() -> int:
    from kasa import Credentials, Device, Discover  # noqa: PLC0415

    host = os.environ.get("TAPO_HOST")
    username = os.environ.get("TAPO_USERNAME")
    password = os.environ.get("TAPO_PASSWORD")
    timeout = int(os.environ.get("TAPO_TIMEOUT", "10"))
    discovery_timeout = int(os.environ.get("TAPO_DISC_TIMEOUT", "5"))

    if not host or not username or not password:
        print(
            "Set TAPO_HOST, TAPO_USERNAME and TAPO_PASSWORD environment "
            "variables before running this script.",
            file=sys.stderr,
        )
        return 2

    credentials = Credentials(username, password)

    print(f"Discovering {host} (timeout={discovery_timeout}s)...")
    device: Device | None = await Discover.discover_single(
        host,
        credentials=credentials,
        discovery_timeout=discovery_timeout,
        timeout=timeout,
    )
    if device is None:
        print("No device found.", file=sys.stderr)
        return 1

    print(f"Discovered: {device.model} ({device.device_type}) at {device.host}")
    print(f"connection_type: {device.config.connection_type}")

    print("Calling update()...")
    await device.update()

    _print_device_features(device)

    if not device.children:
        print("\n(no child devices reported)")
    for child in device.children:
        _print_device_features(child)

    await device.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
