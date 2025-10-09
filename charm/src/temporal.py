#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Temporal service."""

import logging
import time
from pathlib import Path

from charms.operator_libs_linux.v1.systemd import (
    daemon_reload,
    service_enable,
    service_restart,
    service_running,
)
from charms.operator_libs_linux.v2 import snap

SYSTEMD_UNIT_DIR = Path("/etc/systemd/system")

TEMPORAL_PORT = 7233
TEMPORAL_UI_PORT = 8233

TEMPORAL_SYSTEMD_SERVICE_PATH = SYSTEMD_UNIT_DIR / "temporal.service"
TEMPORAL_SYSTEMD_SERVICE = """
[Unit]
Description=Ubuntu Release Temporal server

[Service]
ExecStart=/snap/bin/temporal server start-dev --ip 0.0.0.0 --ui-public-path /ui
Restart=on-failure

[Install]
WantedBy=ubuntu-release-worker.service
"""

logger = logging.getLogger(__name__)


class Temporal:
    """Represent an instance of the Temporal server service."""

    def install(self):
        """Install the Temporal snap package and systemd unit."""
        try:
            self._snap.ensure(snap.SnapState.Latest, channel="stable")
            snap.hold_refresh()
        except snap.SnapError as e:
            logger.error("could not install temporal. Reason: %s", e.message)
            logger.debug(e, exc_info=True)
            raise e

        TEMPORAL_SYSTEMD_SERVICE_PATH.write_text(TEMPORAL_SYSTEMD_SERVICE)
        daemon_reload()

    def start(self):
        """Start the Temporal server."""
        service_enable("temporal")
        tries = 0
        while tries < 6 and not service_running("temporal"):
            service_restart("temporal")
            tries += 1
            time.sleep(tries * 10)

    @property
    def port(self) -> int:
        """Report the port on which the Temporal server is running."""
        return TEMPORAL_PORT

    @property
    def ui_port(self) -> int:
        """Report the port on which the Temporal UI is running."""
        return TEMPORAL_UI_PORT

    @property
    def _snap(self):
        """Return a representation of the Temporal snap."""
        cache = snap.SnapCache()
        return cache["temporal"]
