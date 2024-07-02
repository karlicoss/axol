from abc import abstractmethod, ABC
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Callable, Iterator, Protocol, Self, Sequence

import orjson
from loguru import logger

from .common import Json, SearchResults, DbResult
from .storage import Database
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


ExcludeP = Callable[[bytes], bool]


@dataclass
class Config(Mixin):
    name: str
    queries: Sequence[Query]
    exclude: ExcludeP | None
    # FIXME use in search and retrieval
    # if matched any during retrieval, warn about pruning?

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

    def select_all(self) -> Iterator[DbResult]:
        exclude = self.exclude
        # FIXME read only mode or something?
        # definitely makes sense considering constructor creates the db if it doesn't exist
        total = 0
        excluded = 0
        with Database(self.db_path) as db:
            for uid, crawl_timestamp_utc, blob in db.select_all():
                total += 1
                # FIXME filter out after search as well
                if exclude is not None and exclude(blob):
                    excluded += 1
                    continue
                crawl_dt = datetime.fromtimestamp(crawl_timestamp_utc, tz=timezone.utc)
                j = orjson.loads(blob)
                yield (uid, crawl_dt, j)
        if excluded > 0:
            logger.warning(f"{self}: excluded {excluded}/{total} items based on config. Run 'prune' to purge them from the db.")

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
        exclude: ExcludeP | None = None,
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
        return cls(name=name, queries=_queries, exclude=exclude)


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
