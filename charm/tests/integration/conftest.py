import logging
import os
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

    working_dir = os.getenv("SPREAD_PATH", Path("."))

    subprocess.run(
        ["/snap/bin/charmcraft", "pack", "--verbose"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=working_dir,
        check=True,
    )

    return next(Path.glob(Path(working_dir), "*.charm")).absolute()


@pytest.fixture(scope="module")
def juju() -> Generator[jubilant.Juju, None, None]:
    with jubilant.temp_model() as juju:
        yield juju
