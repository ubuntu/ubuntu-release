#!/usr/bin/env python3
# Copyright 2025 Skia
# See LICENSE file for licensing details.

"""Charm the worker for Ubuntu Release."""

import logging
from subprocess import CalledProcessError

import ops
from charms.haproxy.v1.haproxy_route import HaproxyRouteRequirer
from charms.operator_libs_linux.v2 import snap

from temporal import Temporal
from worker import Worker

logger = logging.getLogger(__name__)


class WorkerCharm(ops.CharmBase):
    """Charm the application."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)

        self._temporal = Temporal()
        self._worker = Worker()

        # This route actually does not work, because haproxy charm doesn't
        # support configuring gRPC backend yet. See TODO bug link
        self.route_temporal = HaproxyRouteRequirer(
            self,
            service="temporal",
            ports=[self._temporal.port],
            paths=["/"],
            relation_name="route_temporal",
        )
        self.route_temporal_ui = HaproxyRouteRequirer(
            self,
            service="temporal_ui",
            ports=[self._temporal.ui_port],
            paths=["/ui"],
            relation_name="route_temporal_ui",
        )

        framework.observe(self.on.install, self._install)
        framework.observe(self.on.upgrade_charm, self._install)
        framework.observe(self.on.config_changed, self._setup_config)

        framework.observe(self.route_temporal.on.ready, self._setup_config)
        framework.observe(self.route_temporal.on.removed, self._setup_config)
        framework.observe(self.route_temporal_ui.on.ready, self._setup_config)
        framework.observe(self.route_temporal_ui.on.removed, self._setup_config)

    def _install(self, event: ops.InstallEvent):
        """Handle install event."""
        self.unit.status = ops.MaintenanceStatus("Installing worker binary")
        self._worker.install()

        self.unit.status = ops.MaintenanceStatus("Installing Temporal binary")
        try:
            self._temporal.install()
        except snap.SnapError as e:
            logger.error("Failed to install Temporal snap: %s", str(e))
            self.unit.status = ops.BlockedStatus("Failed to install Temporal")
            return

        try:
            self.unit.set_workload_version(self._worker.version)
        except CalledProcessError as e:
            self.unit.status = ops.MaintenanceStatus("Failed to determine workload version")
            logger.error("Failed to set workload version: %s", str(e))

    def _setup_config(self, event: ops.ConfigChangedEvent):
        self.unit.status = ops.MaintenanceStatus("Starting Temporal")
        self._temporal.start()
        self.unit.set_ports(self._temporal.port)

        self.unit.status = ops.MaintenanceStatus("Starting worker")
        self._worker.start()

        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main(WorkerCharm)  # type: ignore
