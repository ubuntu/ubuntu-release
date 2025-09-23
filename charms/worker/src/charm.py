#!/usr/bin/env python3
# Copyright 2025 Skia
# See LICENSE file for licensing details.

"""Charm the worker for Ubuntu Release."""

import logging
from pathlib import Path
from subprocess import CalledProcessError, check_call, check_output

import ops
from charms.haproxy.v1.haproxy_route import HaproxyRouteRequirer

logger = logging.getLogger(__name__)

HOME = Path("~ubuntu").expanduser()
REPO_LOCATION = HOME / "ubuntu-release"

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

        framework.observe(self.on.install, self._on_install)
        framework.observe(self.on.config_changed, self._on_config_changed)

        framework.observe(self.route_temporal.on.ready, self._on_config_changed)
        framework.observe(self.route_temporal.on.removed, self._on_config_changed)
        framework.observe(self.route_temporal_ui.on.ready, self._on_config_changed)
        framework.observe(self.route_temporal_ui.on.removed, self._on_config_changed)

    def _on_install(self, event: ops.InstallEvent):
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
                    "golang-go",
                    "vim",
                ]
            )
            # workaround snap'd temporal not able to run in a systemd service for reasons™
            # check_call(["snap", "install", "temporal"])
            # this temporal binary arrived magically "here" with the "dump" plugin in charmcraft.yaml
            check_call(["cp", "temporal", "/usr/bin/temporal"])
        except CalledProcessError as e:
            logger.debug("Package install failed with return code %d", e.returncode)
            self.unit.status = ops.BlockedStatus("Failed installing apt packages.")
            return

        try:
            self.unit.status = ops.MaintenanceStatus("Installing code")
            repo_url = self.config.get("repo-url")
            repo_branch = self.config.get("repo-branch")
            check_call(
                [
                    "sudo",
                    "-u",
                    "ubuntu",
                    "git",
                    "clone",
                    "-b",
                    repo_branch,
                    repo_url,
                    REPO_LOCATION,
                ]
            )
            self.unit.status = ops.ActiveStatus("Ready")
        except CalledProcessError as e:
            logger.debug("Git clone of the code failed with return code %d", e.returncode)
            self.unit.status = ops.BlockedStatus("Failed git cloning the code.")
            return

    def _on_config_changed(self, event: ops.ConfigChangedEvent):
        # Make sure the repo is up to date
        repo_url = self.config.get("repo-url")
        repo_branch = self.config.get("repo-branch")
        self.unit.status = ops.MaintenanceStatus("Fetching latest updates of retracer code")
        check_call(
            [
                "sudo",
                "-u",
                "ubuntu",
                "git",
                "-C",
                REPO_LOCATION,
                "fetch",
                "--update-head-ok",
                "--force",
                repo_url,
                f"refs/heads/{repo_branch}:refs/heads/{repo_branch}",
            ]
        )
        check_call(
            [
                "sudo",
                "-u",
                "ubuntu",
                "git",
                "-C",
                REPO_LOCATION,
                "reset",
                "--hard",
                repo_branch,
            ]
        )

        self.unit.status = ops.MaintenanceStatus("Building worker binary")

        # TODO: move that build step out of the charm deployment, and make that
        # happen around the charmcraft pack operation, in the CI
        check_call(
            [
                "sudo",
                "-u",
                "ubuntu",
                "go",
                "build",
                "-o",
                str(HOME / "bin" / "ubuntu-release-worker"),
                str(REPO_LOCATION / "ubuntu-release-worker" / "main.go"),
            ],
            cwd=REPO_LOCATION,
        )

        systemd_unit_location = Path("/") / "etc" / "systemd" / "system"
        systemd_unit_location.mkdir(parents=True, exist_ok=True)
        self.unit.status = ops.MaintenanceStatus("setting up systemd units")
        (systemd_unit_location / "temporal.service").write_text(
            f"""
[Unit]
Description=Ubuntu Release Temporal server

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory={HOME}
ExecStart=temporal server start-dev --ip 0.0.0.0 --ui-public-path /ui
Restart=on-failure

[Install]
WantedBy=ubuntu-release-worker.service
"""
        )

        (systemd_unit_location / "ubuntu-release-worker.service").write_text(
            f"""
[Unit]
Description=Ubuntu Release Temporal worker

[Service]
User=ubuntu
Group=ubuntu
ExecStart={HOME}/bin/ubuntu-release-worker
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
        self.unit.set_workload_version(self._getWorkloadVersion())
        self.unit.status = ops.ActiveStatus("Ready")

    def _getWorkloadVersion(self):
        """Get the retracer version from the git repository"""
        try:
            self.unit.status = ops.MaintenanceStatus("fetching code version")
            version = check_output(
                [
                    "sudo",
                    "-u",
                    "ubuntu",
                    "git",
                    "-C",
                    REPO_LOCATION,
                    "describe",
                    "--tags",
                    "--always",
                    "--dirty",
                ]
            )
            return version.decode()
        except CalledProcessError as e:
            logger.debug("Unable to get workload version (%d, %s)", e.returncode, e.stderr)
            self.unit.status = ops.BlockedStatus("Failed git describe.")


if __name__ == "__main__":  # pragma: nocover
    ops.main(WorkerCharm)  # type: ignore
