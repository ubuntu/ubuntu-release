import logging
import os

import jubilant

from conftest import charm_path, rock_path

logger = logging.getLogger()


def test_deploy(juju: jubilant.Juju, repo_sha: str):
    resource_location = None
    if "CI" not in os.environ:
        resource_location = rock_path("worker")
        logger.info("Not running in CI, using local rock path: %s", resource_location)
    else:
        resource_location = "ghcr.io/ubuntu/ubuntu-release/ubuntu-release-worker:" + repo_sha
        logger.info("Running in CI, using GHCR rock address: %s", resource_location)

    juju.deploy(
        charm=charm_path("worker"),
        app="worker",
        resources={"ubuntu-release-worker-image": resource_location},
    )

    juju.wait(lambda status: jubilant.all_active(status, "worker"), timeout=600)
