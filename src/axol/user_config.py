import os
from pathlib import Path
from typing import Iterator

from axol.core.config import Config


assert 'PYTEST_CURRENT_TEST' not in os.environ  # to make sure we don't test agains user config


STORAGE_DIR: Path


def configs() -> Iterator[Config]:
    raise NotImplementedError
