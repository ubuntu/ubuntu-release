#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Worker service."""

import logging
import shutil
from pathlib import Path
from subprocess import CalledProcessError, check_output

from charms.operator_libs_linux.v1.systemd import (
    daemon_reload,
    service_enable,
    service_restart,
)

WORKER_BINARY = Path("ubuntu-release-worker")
WORKER_BINARY_PATH = Path("/usr/bin/ubuntu-release-worker")

SYSTEMD_UNIT_DIR = Path("/etc/systemd/system")
WORKER_SYSTEMD_SERVICE_PATH = SYSTEMD_UNIT_DIR / "ubuntu-release-worker.service"
WORKER_SYSTEMD_SERVICE = """
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

logger = logging.getLogger(__name__)


class Worker:
    """Represent an instance of the Ubuntu Release Worker service."""

    def install(self):
        """Install the Ubuntu Release Worker binary and systemd unit."""
        shutil.copy(WORKER_BINARY, WORKER_BINARY_PATH)
        WORKER_SYSTEMD_SERVICE_PATH.write_text(WORKER_SYSTEMD_SERVICE)
        daemon_reload()

    def start(self):
        """Start the Temporal server."""
        service_enable("ubuntu-release-worker")
        service_restart("ubuntu-release-worker")

    @property
    def version(self):
        """Return the version of the Ubuntu Release Worker binary."""
        try:
            version = check_output(["ubuntu-release-worker", "--version"]).strip()
            return version.decode()
        except CalledProcessError as e:
            logger.error("Unable to get workload version (%d, %s)", e.returncode, e.stderr)
