#!/usr/bin/env python3
# Copyright 2025 Skia
# See LICENSE file for licensing details.

"""Charm the worker for Ubuntu Release."""

import ops


class WorkerCharm(ops.CharmBase):
    """Charm the application."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)
        self.unit.status = ops.ActiveStatus("Ready")


if __name__ == "__main__":  # pragma: nocover
    ops.main(WorkerCharm)  # type: ignore
