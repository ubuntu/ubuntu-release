# Copyright 2025 Canonical
# See LICENSE file for licensing details.

"""Functional tests for the temporal module.

These tests will manipulate the underlying machine, and thus are
run in a fresh VM with spread.
"""

import pytest
import requests
from charms.operator_libs_linux.v1.systemd import service_running
from charms.operator_libs_linux.v2 import snap
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from temporal import TEMPORAL_SYSTEMD_SERVICE_PATH, TEMPORAL_UI_PORT, Temporal


@pytest.fixture
def temporal():
    return Temporal()


def test_install_temporal(temporal):
    temporal.install()

    # Ensure that packages are installed.
    cache = snap.SnapCache()
    temporal = cache["temporal"]
    assert temporal.present

    # Ensure the systemd service has been created.
    assert TEMPORAL_SYSTEMD_SERVICE_PATH.exists()


def test_restart_temporal(temporal):
    temporal.start()
    assert service_running("temporal")

    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    response = session.get(f"http://localhost:{TEMPORAL_UI_PORT}/ui/")

    assert response.status_code == 200
    assert """<link rel="modulepreload" href="/ui/_app/immutable/entry/start""" in response.text
