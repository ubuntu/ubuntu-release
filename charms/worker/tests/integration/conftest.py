import logging
from pathlib import Path
from typing import Generator

import jubilant
import pytest

logger = logging.getLogger()


@pytest.fixture(scope="module")
def worker_charm_path() -> Path:
    """Return full absolute path to given test charm."""
    charm_dir = Path(__file__).parent / "worker"
    charms = [p.absolute() for p in charm_dir.glob("ubuntu-release-worker_*.charm")]
    assert charms, "ubuntu-release-worker_*.charm not found"
    assert len(charms) == 1, "more than one .charm file, unsure which to use"
    return charms[0]


@pytest.fixture(scope="module")
def juju() -> Generator[jubilant.Juju, None, None]:
    with jubilant.temp_model() as juju:
        yield juju
