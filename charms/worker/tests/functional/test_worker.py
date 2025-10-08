# Copyright 2025 Canonical
# See LICENSE file for licensing details.

"""Functional tests for the worker module.

These tests will manipulate the underlying machine, and thus are
run in a fresh VM with spread.
"""

import pytest
from charms.operator_libs_linux.v1.systemd import service_running

from temporal import Temporal
from worker import WORKER_BINARY_PATH, WORKER_SYSTEMD_SERVICE_PATH, Worker


@pytest.fixture
def worker():
    temporal = Temporal()
    temporal.install()
    temporal.start()
    return Worker()


def test_install_worker(worker):
    worker.install()
    # Ensure the binary was installed.
    assert WORKER_BINARY_PATH.exists()
    # Ensure the systemd service has been created.
    assert WORKER_SYSTEMD_SERVICE_PATH.exists()


def test_restart_worker(worker):
    worker.start()
    assert service_running("ubuntu-release-worker")
