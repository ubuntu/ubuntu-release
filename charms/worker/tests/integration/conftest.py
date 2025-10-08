import logging
import subprocess
from pathlib import Path
from typing import Generator

import jubilant
import pytest

logger = logging.getLogger()


@pytest.fixture(scope="module")
def worker_charm_path(request):
    charm_file = request.config.getoption("--charm-path")
    if charm_file:
        return charm_file

    subprocess.run(
        ["/snap/bin/charmcraft", "pack", "--verbose"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    return next(Path.glob(Path("."), "*.charm")).absolute()


@pytest.fixture(scope="module")
def juju() -> Generator[jubilant.Juju, None, None]:
    with jubilant.temp_model() as juju:
        yield juju
