import logging
from pathlib import Path
import subprocess

import jubilant
import pytest

logger = logging.getLogger()


def charm_path(name: str) -> Path:
    """Return full absolute path to given test charm."""
    charm_dir = Path(__file__).parent / name
    charms = [p.absolute() for p in charm_dir.glob(f"ubuntu-release-{name}_*.charm")]
    assert charms, f"ubuntu-release-{name}_*.charm not found"
    assert len(charms) == 1, "more than one .charm file, unsure which to use"
    return charms[0]


def rock_path(name: str) -> Path:
    """Return full absolute path to given test rock."""
    root_dir = Path(__file__).parent.parent
    print(root_dir)
    rocks = [p.absolute() for p in root_dir.glob(f"ubuntu-release-{name}_*.rock")]
    print(rocks)
    assert rocks, f"ubuntu-release-{name}_*.rock not found"
    assert len(rocks) == 1, "more than one .rock file, unsure which to use"
    return rocks[0]


@pytest.fixture(scope="module")
def repo_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()


@pytest.fixture(scope="module")
def juju() -> jubilant.Juju:
    with jubilant.temp_model() as juju:
        yield juju
