import logging
import os

import jubilant

from conftest import charm_path, rock_path

logger = logging.getLogger()


def test_deploy(juju: jubilant.Juju, repo_sha: str):
    resource_location = None
    if "CI" not in os.environ:
        # XXX: this actually doesn't work because of https://bugs.launchpad.net/juju/+bug/1935707
        resource_location = rock_path("worker")
        # we would likely need to do this instead, so you'd need to manually run a registry and push to it:
        #   $ docker run -d -p 5000:5000 --name registry registry:latest
        #   $ rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
        #       oci-archive:ubuntu-release-worker_0.1_amd64.rock \
        #       docker://localhost:5000/ubuntu-release-worker:$(git rev-parse HEAD)
        # and then use the following:
        # resource_location = "localhost:5000/ubuntu-release-worker:" + repo_sha
        # unfortunately, this doesn't work either in all cases, because
        # depending on how you installed microk8s, it might not be able to reach
        # localhost:5000, or in my case, even after some hackery, it's complaining about
        # receiving an HTTP response when it expected HTTPS 😢
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
