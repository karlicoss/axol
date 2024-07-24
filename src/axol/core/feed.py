from abc import abstractmethod, ABC
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Callable, Generic, Iterable, Iterator, Protocol, Self, Sequence, TypeVar

from loguru import logger

from .common import SearchResults, Uid
from .storage import CrawlDt, Database
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
    exclude: Callable[[ResultType], bool] | None
    exclude_raw: ExcludeP | None

    @abstractmethod
    def parse(self, data: bytes) -> ResultType:
        raise NotImplementedError

    @property
    @abstractmethod
    def search(self) -> SearchF:
        raise NotImplementedError

    @property
    def _excluder(self) -> Callable[[bytes], bool] | None:
        exclude_raw = self.exclude_raw
        exclude = self.exclude
        if exclude is not None:
            assert exclude_raw is None  # otherwise unclear which to pick

            exclude_raw = lambda blob: exclude(self.parse(blob))

        if exclude_raw is None:
            return None

        def exclude_raw_defensive(data: bytes) -> bool:
            try:
                return exclude_raw(data)
            except Exception as e:
                logger.error(f'error while evaluating exclude function for {data!r}')
                logger.exception(e)
                # stay on the safe side
                return False

        return exclude_raw_defensive

    def search_all(self, *, limit: int | None) -> Iterator[tuple[Uid, bytes]]:
        excluder = self._excluder
        search_queries = compile_queries(self.queries)
        handled = set()
        for search_query in search_queries:
            for uid, data in self.search(query=search_query, limit=limit):
                # TODO check that items coming from the same search query are already made unique?
                # dunno if this is really necessary though
                # but could be a sign of wrong pagination or smth like that
                if uid in handled:
                    continue
                handled.add(uid)

                if excluder is not None and excluder(data):
                    continue

                # todo could yield query here? not sure if super useful
                yield uid, data

    def _insert(
        self,
        results: Iterable[tuple[Uid, bytes]],
        dry: bool,
    ) -> Iterator[tuple[CrawlDt, Uid, bytes]]:
        writable = not dry
        with Database(self.db_path, writable=writable) as db:
            yield from db.insert(results, dry=dry)

    def _select_all(self) -> Iterator[tuple[CrawlDt, Uid, bytes]]:
        excluder = self._excluder
        total = 0
        excluded = 0
        # TODO when querying, also use stored procedure like in prune_db?
        # compare performance??
        with Database(self.db_path) as db:
            for crawl_timestamp_utc, uid, blob in db.select_all():
                total += 1
                if excluder is not None and excluder(blob):
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
        excluder = self._excluder
        if excluder is None:
            logger.info('feed has no exclude function defined, nothing to do')
            # fast path
            return 0

        writable = not dry
        with Database(self.db_path, writable=writable) as db:
            deleted = db.delete(dry=dry, predicate=excluder)
        return deleted
        # TODO interactive mode? for now just use --dry

    def crawl(self, *, limit: int | None = None, dry: bool = False) -> Iterator[tuple[CrawlDt, Uid, ResultType | Exception]]:
        # convert to list to make sure the connection in _insert isn't open for long
        # sort by crawl_dt and uid cause why not?
        results = sorted(self.search_all(limit=limit))

        # convert to list to make sure we actually inserted things before attempting to parse
        inserted = list(self._insert(results, dry=dry))

        yield from self._parsed(inserted)

    def feed(self) -> Iterator[tuple[CrawlDt, Uid, ResultType | Exception]]:
        yield from self._parsed(self._select_all())

    def _parsed(self, results: Iterable[tuple[CrawlDt, Uid, bytes]]) -> Iterator[tuple[CrawlDt, Uid, ResultType | Exception]]:
        for crawl_dt, uid, data in results:
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
        exclude: Callable[[ResultType], bool] | None = None,
        exclude_raw: ExcludeP | None = None,
    ) -> Self:
        assert re.fullmatch(r'[\w\.]+', query_name)

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

        assert not (exclude is not None and exclude_raw is not None)
        return cls(name=name, db_path=db_path, queries=_queries, exclude=exclude, exclude_raw=exclude_raw)


def storage_dir() -> Path:
    import axol.user_config as C

    res = C.STORAGE_DIR
    return res


def get_feeds(*, include: str | None = None, exclude: str | None = None) -> list[Feed]:
    assert not (include is not None and exclude is not None)

    import axol.user_config as C

    feeds = list(C.feeds())
    if include is not None:
        feeds = [c for c in feeds if re.match(include, c.name)]
    if exclude is not None:
        feeds = [c for c in feeds if not re.match(exclude, c.name)]
    assert len(feeds) > 0
    return feeds
