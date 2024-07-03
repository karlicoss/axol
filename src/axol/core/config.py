from abc import abstractmethod, ABC
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Iterator, Protocol, Self, Sequence

import orjson
from loguru import logger

from .common import Json, SearchResults, DbResult, Uid
from .storage import Database
from .query import compile_queries


# the searcher decides on the query type itself?
# TODO make these two typed? not sure how.. maybe use Compilable protocol?
Query = Any
SearchQuery = Any


class SearchF(Protocol):
    # TODO typed query??
    def __call__(self, query: SearchQuery, *, limit: int | None) -> SearchResults: ...


class Mixin(ABC):
    PREFIX: str = NotImplemented
    QueryType: type = NotImplemented


ExcludeP = Callable[[bytes], bool]


# FIXME maybe feed is a better name??
@dataclass
class Config(Mixin):
    name: str
    queries: Sequence[Query]
    db_path: Path
    exclude: ExcludeP | None

    @abstractmethod
    def parse(self, j: Json):
        # TODO not sure about this.. also kinda annoying it erases the type..
        raise NotImplementedError

    @property
    @abstractmethod
    def search(self) -> SearchF:
        raise NotImplementedError

    def search_all(self, *, limit: int | None) -> Iterator[tuple[Uid, bytes]]:
        exclude = self.exclude

        search_queries = compile_queries(self.queries)
        handled = set()
        for search_query in search_queries:
            for uid, j in self.search(query=search_query, limit=limit):
                if uid in handled:
                    continue
                handled.add(uid)

                jblob = orjson.dumps(j)
                if exclude is not None and exclude(jblob):
                    continue

                # TODO could yield query here?
                yield uid, jblob

    def insert(self, results: Iterable[tuple[Uid, bytes]]) -> None:
        # todo return inserted count?
        # todo not sure if need to use self.exclude here?
        with Database(self.db_path, writable=True) as db:
            db.insert(results)

    def select_all(self) -> Iterator[DbResult]:
        exclude = self.exclude
        total = 0
        excluded = 0
        with Database(self.db_path) as db:
            for uid, crawl_timestamp_utc, blob in db.select_all():
                total += 1
                if exclude is not None and exclude(blob):
                    excluded += 1
                    continue
                crawl_dt = datetime.fromtimestamp(crawl_timestamp_utc, tz=timezone.utc)
                j = orjson.loads(blob)
                yield (uid, crawl_dt, j)
        if excluded > 0:
            logger.warning(f"{self}: excluded {excluded}/{total} items based on config. Run 'prune' to purge them from the db.")

    @classmethod
    def make(
        cls: type[Self],
        *,
        db_path: str | Path | None = None,
        query_name: str,
        queries: Sequence[Query | str],
        exclude: ExcludeP | None = None,
    ) -> Self:
        assert re.fullmatch(r'\w+', query_name)

        PREFIX = cls.PREFIX
        assert PREFIX is not None, cls
        name = PREFIX + '_' + query_name

        if db_path is None:
            db_path = name + '.sqlite'

        if isinstance(db_path, str):
            db_path = Path(db_path)

        if not db_path.is_absolute():
            db_path = storage_dir() / db_path

        assert isinstance(queries, (list, tuple))
        _queries: list[Query] = []
        for query in queries:
            if isinstance(query, str):
                _queries.append(cls.QueryType(query))
            else:
                _queries.append(query)
        assert len(_queries) > 0
        return cls(name=name, db_path=db_path, queries=_queries, exclude=exclude)


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
