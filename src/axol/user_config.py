import os
from collections.abc import Iterator
from pathlib import Path

from axol.core.feed import Feed

assert 'PYTEST_CURRENT_TEST' not in os.environ  # to make sure we don't test against user config


STORAGE_DIR: Path


def feeds() -> Iterator[Feed]:
    raise NotImplementedError
