from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .common import Json, SearchResults


# the searcher decides on the query type itself?
Query = Any


@dataclass
class Config:
    name: str
    queries: Sequence[Query]

    @abstractmethod
    def parse(self, j: Json):
        # TODO not sure about this.. also kinda annoying it erases the type..
        raise NotImplementedError

    @abstractmethod
    def search(self, *, query: Query, limit: int | None) -> SearchResults:
        # FIXME maybe doesn't need to accept queries??
        raise NotImplementedError

    @property
    def db_path(self) -> Path:
        return storage_dir() / f'{self.name}.sqlite'  # FIXME slugify


def storage_dir() -> Path:
    import axol.user_config as C
    res = C.STORAGE_DIR
    assert res.is_dir(), res
    return res
