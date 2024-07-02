from abc import abstractmethod, ABC
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Protocol, Self, Sequence

from .common import Json, SearchResults
from .query import compile_queries


# the searcher decides on the query type itself?
# TODO make these two typed? not sure how..
Query = Any
SearchQuery = Any


class SearchF(Protocol):
    # FIXME query type?
    def __call__(self, query: SearchQuery, *, limit: int | None) -> SearchResults:
        ...


class Mixin(ABC):
    PREFIX: str = NotImplemented
    QueryType: type = NotImplemented


@dataclass
class Config(Mixin):
    name: str
    queries: Sequence[Query]

    @abstractmethod
    def parse(self, j: Json):
        # TODO not sure about this.. also kinda annoying it erases the type..
        raise NotImplementedError

    @property
    @abstractmethod
    def search(self) -> SearchF:
        raise NotImplementedError

    def search_all(self, *, limit: int | None) -> SearchResults:
        search_queries = compile_queries(self.queries)
        handled = set()
        for search_query in search_queries:
            for uid, j in self.search(query=search_query, limit=limit):
                if uid in handled:
                    continue
                handled.add(uid)
                # TODO could yield query here?
                yield uid, j

    @property
    def db_path(self) -> Path:
        return storage_dir() / f'{self.name}.sqlite'  # FIXME slugify

    @classmethod
    def make(
        cls: type[Self],
        *,
        name: str | None = None,
        query_name: str | None = None,
        queries: Sequence[Query | str],
    ) -> Self:
        assert (name is None) ^ (query_name is None)
        if name is None:
            # build from query_name and prefix
            assert query_name is not None
            PREFIX = cls.PREFIX
            assert PREFIX is not None, cls
            name = PREFIX + '_' + query_name

        assert isinstance(queries, (list, tuple))
        _queries: list[Query] = []
        for query in queries:
            if isinstance(query, str):
                _queries.append(cls.QueryType(query))
            else:
                _queries.append(query)
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
        configs = [c for c in configs if re.search(include, c.name)]
    assert len(configs) > 0
    return configs
