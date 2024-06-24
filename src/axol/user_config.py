from pathlib import Path
from typing import Iterator

from axol.core.config import Config


STORAGE_DIR: Path


def configs() -> Iterator[Config]:
    raise NotImplementedError
