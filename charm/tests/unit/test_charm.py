# Copyright 2025 Canonical
# See LICENSE file for licensing details.

"""Unit tests for the charm.

These tests only cover those methods that do not require internet access,
and do not attempt to manipulate the underlying machine.
"""

from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import PropertyMock, patch

import pytest
import yaml
from charms.operator_libs_linux.v2 import snap
from ops.testing import ActiveStatus, BlockedStatus, Context, MaintenanceStatus, State

from charm import WorkerCharm


@pytest.fixture
def ctx():
    charmcraft_yaml_path = Path(__file__).parent.parent.parent.parent / "charmcraft.yaml"
    meta = yaml.safe_load((charmcraft_yaml_path).read_text())
    return Context(WorkerCharm, meta=meta)


@pytest.fixture
def base_state(ctx):
    return State(leader=True)


@patch("charm.Temporal.install")
@patch("charm.Worker.install")
@patch("charm.Worker.version", new_callable=PropertyMock)
def test_install_success(
    version_mock, worker_install_mock, temporal_install_mock, ctx, base_state
):
    temporal_install_mock.return_value = True
    worker_install_mock.return_value = True
    version_mock.return_value = "1.0.0"
    out = ctx.run(ctx.on.install(), base_state)
    assert out.unit_status == MaintenanceStatus("Installing Temporal binary")
    assert temporal_install_mock.called
    assert worker_install_mock.called


@patch("charm.Temporal.install")
@patch("charm.Worker.install")
@patch("charm.Worker.version", new_callable=PropertyMock)
def test_install_failure(
    version_mock, worker_install_mock, temporal_install_mock, ctx, base_state
):
    temporal_install_mock.side_effect = snap.SnapError
    worker_install_mock.return_value = True
    version_mock.return_value = "1.0.0"
    out = ctx.run(ctx.on.install(), base_state)
    assert out.unit_status == BlockedStatus("Failed to install Temporal")


@patch("charm.Temporal.install")
@patch("charm.Worker.install")
@patch("charm.Worker.version", new_callable=PropertyMock)
def test_install_failure_to_set_workload_version(
    version_mock, worker_install_mock, temporal_install_mock, ctx, base_state
):
    temporal_install_mock.return_value = True
    worker_install_mock.return_value = True
    version_mock.side_effect = CalledProcessError(1, "foo")
    out = ctx.run(ctx.on.install(), base_state)
    assert out.unit_status == MaintenanceStatus("Failed to determine workload version")


@patch("charm.Temporal.install")
@patch("charm.Worker.install")
@patch("charm.Worker.version", new_callable=PropertyMock)
def test_upgrade_success(
    version_mock, worker_install_mock, temporal_install_mock, ctx, base_state
):
    temporal_install_mock.return_value = True
    worker_install_mock.return_value = True
    version_mock.return_value = "1.0.0"
    out = ctx.run(ctx.on.upgrade_charm(), base_state)
    assert out.unit_status == MaintenanceStatus("Installing Temporal binary")
    assert temporal_install_mock.called
    assert worker_install_mock.called


@patch("charm.Temporal.start")
@patch("charm.Worker.start")
def test_config_changed(start_worker_mock, start_temporal_mock, ctx, base_state):
    out = ctx.run(ctx.on.config_changed(), base_state)
    assert start_worker_mock.called
    assert start_temporal_mock.called
    assert out.unit_status == ActiveStatus()
