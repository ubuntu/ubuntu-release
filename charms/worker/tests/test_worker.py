import logging

import jubilant
from requests import Session

from conftest import charm_path

from . import DNSResolverHTTPSAdapter

logger = logging.getLogger()

UR_WORKER = "ubuntu-release-worker"
HAPROXY = "haproxy"
SSC = "self-signed-certificates"


def test_deploy(juju: jubilant.Juju):
    juju.deploy(
        charm=charm_path("worker"),
        app=UR_WORKER,
    )
    juju.deploy(
        HAPROXY, channel="2.8/edge", config={"external-hostname": "ubuntu-release.internal"}
    )
    juju.deploy(SSC, channel="1/edge")

    juju.integrate(HAPROXY + ":certificates", SSC + ":certificates")
    juju.integrate(UR_WORKER + ":route_temporal_ui", HAPROXY)
    # Doesn't work yet
    # juju.integrate(UR_WORKER + ":route_temporal", HAPROXY)

    juju.wait(lambda status: jubilant.all_active(status, UR_WORKER, HAPROXY, SSC), timeout=1800)


def test_ingress_functions_correctly(juju: jubilant.Juju):
    model_name = juju.model
    assert model_name is not None

    haproxy_ip = juju.status().apps[HAPROXY].units[f"{HAPROXY}/0"].public_address
    external_hostname = "ubuntu-release.internal"

    session = Session()
    session.mount("https://", DNSResolverHTTPSAdapter(external_hostname, haproxy_ip))
    response = session.get(
        f"https://{haproxy_ip}/ui/",
        headers={"Host": external_hostname},
        verify=False,
        timeout=30,
    )

    assert response.status_code == 200
    assert """<link rel="modulepreload" href="/ui/_app/immutable/entry/start""" in response.text
