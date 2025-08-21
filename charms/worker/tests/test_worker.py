import logging

import jubilant

from conftest import charm_path

logger = logging.getLogger()


def test_deploy(juju: jubilant.Juju):
    juju.deploy(
        charm=charm_path("worker"),
        app="worker",
    )

    juju.wait(lambda status: jubilant.all_active(status, "worker"), timeout=600)
