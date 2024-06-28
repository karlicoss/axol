from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Self, Sequence

from .common import Json, SearchResults


# the searcher decides on the query type itself?
Query = Any


class Mixin(Protocol):
    PREFIX: str


@dataclass
class Config(Mixin):
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

    @classmethod
    def make(
        cls: type[Self],
        *,
        name: str | None = None,
        query_name: str | None = None,
        queries,
    ) -> Self:
        assert (name is None) ^ (query_name is None)
        if name is None:
            # build from query_name and prefix
            assert query_name is not None
            PREFIX = cls.PREFIX
            assert PREFIX is not None, cls
            name = PREFIX + '_' + query_name

        _queries: Sequence[Query]
        if isinstance(queries, (list, tuple)):
            _queries = queries
        else:
            _queries = [queries]
        return cls(name=name, queries=_queries)


def storage_dir() -> Path:
    import axol.user_config as C
    res = C.STORAGE_DIR
    assert res.is_dir(), res
    return res


def get_configs(*, include: str | None) -> list[Config]:
    import axol.user_config as C
    configs = list(C.configs())
    if include is not None:
        configs = [c for c in configs if include in c.name]
    assert len(configs) > 0
    return configs
