import logging

import jubilant

from conftest import charm_path

logger = logging.getLogger()


def test_deploy(juju: jubilant.Juju, repo_sha: str):
    juju.deploy(
        charm=charm_path("worker"),
        app="worker",
        resources={
            "ubuntu-release-worker": "ghcr.io/ubuntu/ubuntu-release/ubuntu-release-worker:"
            + repo_sha
        },
    )

    juju.wait(lambda status: jubilant.all_active(status, "worker"), timeout=600)
