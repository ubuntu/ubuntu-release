#!/usr/bin/env python3
# Copyright 2025 Skia
# See LICENSE file for licensing details.

"""Charm the worker for Ubuntu Release."""

import logging
from pathlib import Path
from subprocess import CalledProcessError, call, check_call, check_output

import ops
from charms.haproxy.v1.haproxy_route import HaproxyRouteRequirer

logger = logging.getLogger(__name__)

HOME = Path("~ubuntu").expanduser()

TEMPORAL_PORT = 7233
TEMPORAL_UI_PORT = 8233


class WorkerCharm(ops.CharmBase):
    """Charm the application."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)

        # This route actually does not work, because haproxy charm doesn't
        # support configuring gRPC backend yet. See TODO bug link
        self.route_temporal = HaproxyRouteRequirer(
            self,
            service="temporal",
            ports=[TEMPORAL_PORT],
            paths=["/"],
            relation_name="route_temporal",
        )
        self.route_temporal_ui = HaproxyRouteRequirer(
            self,
            service="temporal_ui",
            ports=[TEMPORAL_UI_PORT],
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
        try:
            self.unit.status = ops.MaintenanceStatus("Installing apt dependencies")
            check_call(["apt-get", "update", "-y"])
            check_call(
                [
                    "apt-get",
                    "install",
                    "-y",
                    "git",
                    "vim",
                ]
            )

            # Those might fail upon first install, but it's no problem. We just
            # want to make sure the processes are shutdown before copying new binaries.
            call(["systemctl", "stop", "temporal"])
            call(["systemctl", "stop", "ubuntu-release-worker"])

            # workaround snap'd temporal not able to run in a systemd service for reasons™
            # check_call(["snap", "install", "temporal"])
            # this temporal binary arrived magically "here" with the "dump" plugin in charmcraft.yaml
            self.unit.status = ops.MaintenanceStatus("Installing Temporal binary")
            check_call(["cp", "temporal", "/usr/bin/temporal"])
            # Install the ubuntu-release-worker binary
            self.unit.status = ops.MaintenanceStatus("Installing Ubuntu Release worker binary")
            check_call(["cp", "ubuntu-release-worker", "/usr/bin/ubuntu-release-worker"])
        except CalledProcessError as e:
            logger.debug("Package install failed with return code %d", e.returncode)
            self.unit.status = ops.BlockedStatus("Failed installing apt packages.")
            return

        self.unit.set_workload_version(self._getWorkloadVersion())

        self.unit.status = ops.ActiveStatus("Ready")

    def _setup_config(self, event: ops.ConfigChangedEvent):
        systemd_unit_location = Path("/") / "etc" / "systemd" / "system"
        systemd_unit_location.mkdir(parents=True, exist_ok=True)
        self.unit.status = ops.MaintenanceStatus("setting up systemd units")
        (systemd_unit_location / "temporal.service").write_text(
            """
[Unit]
Description=Ubuntu Release Temporal server

[Service]
User=ubuntu
Group=ubuntu
ExecStart=temporal server start-dev --ip 0.0.0.0 --ui-public-path /ui
Restart=on-failure

[Install]
WantedBy=ubuntu-release-worker.service
"""
        )

        (systemd_unit_location / "ubuntu-release-worker.service").write_text(
            """
[Unit]
Description=Ubuntu Release Temporal worker

[Service]
User=ubuntu
Group=ubuntu
ExecStart=ubuntu-release-worker
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
        )

        check_call(["systemctl", "daemon-reload"])
        self.unit.status = ops.MaintenanceStatus("enabling systemd units")
        check_call(["systemctl", "enable", "temporal"])
        check_call(["systemctl", "enable", "ubuntu-release-worker"])
        self.unit.status = ops.MaintenanceStatus("restarting systemd units")
        check_call(["systemctl", "restart", "temporal"])
        check_call(["systemctl", "restart", "ubuntu-release-worker"])
        # Temporarily expose the temporal port, since HAProxy is unable to proxy gRPC
        self.unit.set_ports(TEMPORAL_PORT)
        self.unit.status = ops.ActiveStatus("Ready")

    def _getWorkloadVersion(self):
        """Get the retracer version from the git repository"""
        try:
            self.unit.status = ops.MaintenanceStatus("fetching worker version")
            version = check_output(["ubuntu-release-worker", "--version"]).strip()
            return version.decode()
        except CalledProcessError as e:
            logger.debug("Unable to get workload version (%d, %s)", e.returncode, e.stderr)
            self.unit.status = ops.BlockedStatus("Failed fetching version describe.")


if __name__ == "__main__":  # pragma: nocover
    ops.main(WorkerCharm)  # type: ignore
