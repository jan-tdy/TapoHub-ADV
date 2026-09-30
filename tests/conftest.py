# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared test fixtures for the Tapo Hub integration tests."""

from __future__ import annotations

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Make custom_components/ discoverable by Home Assistant during tests."""
    yield
