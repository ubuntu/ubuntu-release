import logging

import jubilant

logger = logging.getLogger()

UR_WORKER = "ubuntu-release-worker"


def test_deploy(juju: jubilant.Juju, worker_charm_path):
    juju.deploy(charm=worker_charm_path, app=UR_WORKER)
    juju.wait(lambda status: jubilant.all_active(status, UR_WORKER), timeout=1800)
