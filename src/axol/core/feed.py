from abc import abstractmethod, ABC
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Callable, Generic, Iterable, Iterator, Protocol, Self, Sequence, TypeVar

from loguru import logger

from .common import datetime_aware, SearchResults, Uid
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


ResultType = TypeVar('ResultType')


@dataclass
class Feed(Mixin, Generic[ResultType]):
    name: str
    queries: Sequence[Query]
    db_path: Path
    exclude: ExcludeP | None

    @abstractmethod
    def parse(self, data: bytes) -> ResultType:
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
            for uid, data in self.search(query=search_query, limit=limit):
                if uid in handled:
                    continue
                handled.add(uid)

                if exclude is not None and exclude(data):
                    continue

                # todo could yield query here? not sure if super useful
                yield uid, data

    def _insert(
        self,
        results: Iterable[tuple[Uid, bytes]],
        dry: bool,
    ) -> Iterator[tuple[datetime_aware, Uid, bytes]]:
        writable = not dry
        with Database(self.db_path, writable=writable) as db:
            yield from db.insert(results, dry=dry)

    def select_all(self) -> Iterator[tuple[datetime_aware, Uid, bytes]]:
        exclude = self.exclude
        total = 0
        excluded = 0
        # TODO when querying, also use stored procedure?
        # compare performance??
        with Database(self.db_path) as db:
            for crawl_timestamp_utc, uid, blob in db.select_all():
                total += 1
                if exclude is not None and exclude(blob):
                    excluded += 1
                    continue
                # TODO crawl_dt deserialize could be inside the db bit?
                # or the other way round.. move timestamp generation into
                crawl_dt = datetime.fromtimestamp(crawl_timestamp_utc, tz=timezone.utc)
                yield (crawl_dt, uid, blob)
        if excluded > 0:
            logger.warning(f"{self}: excluded {excluded}/{total} items based on config. Run 'prune' to purge them from the db.")

    def prune_db(self, *, dry: bool = False) -> int:
        """
        Returns number of pruned items
        """
        # TODO would be nice to yield items to be pruned? at least for dry mode?
        exclude = self.exclude
        if exclude is None:
            # fast path
            return 0

        writable = not dry
        with Database(self.db_path, writable=writable) as db:
            deleted = db.delete(dry=dry, predicate=exclude)
        return deleted
        # TODO interactive mode? for now just use --dry

    def crawl(self, *, limit: int | None = None, dry: bool = False) -> Iterator[tuple[datetime_aware, Uid, bytes]]:
        # convert to list to make sure the connection in _insert isn't open for long
        results = list(self.search_all(limit=limit))
        yield from self._insert(results, dry=dry)
        # TODO after that could try parsing from newly inserted results?
        # but do atomically (force the iterator) to make sure stuff is inserted before parsing

    def feed(self) -> Iterator[tuple[datetime_aware, Uid, ResultType | Exception]]:
        for crawl_dt, uid, data in self.select_all():
            o: ResultType | Exception
            try:
                o = self.parse(data)
            except Exception as e:
                # todo maybe log or something?
                err = RuntimeError(f'while parsing {data!r}')
                err.__cause__ = e
                o = err
            yield crawl_dt, uid, o

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
    return res


def get_feeds(*, include: str | None) -> list[Feed]:
    import axol.user_config as C

    feeds = list(C.feeds())
    if include is not None:
        feeds = [c for c in feeds if re.search(include, c.name)]
    assert len(feeds) > 0
    return feeds
