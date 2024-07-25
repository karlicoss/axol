from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

import orjson

from axol.core.common import Json, Uid
from axol.core.feed import Feed as BaseFeed, SearchF


@dataclass
class SearchQuery:
    query: str


@dataclass
class Query:
    query: str

    def compile(self) -> Iterator[SearchQuery]:
        yield SearchQuery(query=self.query)


@dataclass
class DummyFeed(BaseFeed[Json, Query]):
    PREFIX = 'dummy'
    QueryCls = str

    def parse(self, data: bytes) -> Json:
        return orjson.loads(data)

    @property
    def search(self) -> SearchF:
        def _search(query: SearchQuery, *, limit: int | None):
            for i in range(100):
                uid = f'{i:03d}'
                j = {'text': f'item {uid}'}
                yield uid, orjson.dumps(j)

        return _search

    def asdict(self) -> dict[Uid, Json]:
        d: dict[Uid, Json] = {}
        for crawl_dt, uid, o in self.feed():
            assert uid not in d  # just in case
            assert not isinstance(o, Exception)
            d[uid] = o
        return d


def make_feed(
    *,
    tmp_path: Path,
    exclude_raw: Callable[[bytes], bool] | None = None,
    exclude: Callable[[Json], bool] | None = None,
    query_name: str = 'testing',
) -> DummyFeed:
    return DummyFeed.make(
        query_name=query_name,
        queries=[Query('whatever')],
        db_path=tmp_path / f'{query_name}.sqlite',
        exclude_raw=exclude_raw,
        exclude=exclude,
    )


def test_crawl(tmp_path: Path) -> None:
    feed = make_feed(tmp_path=tmp_path)
    crawled = list(feed.crawl())
    assert len(crawled) == 100

    data = list(feed.feed())
    assert len(data) == 100


def test_prune_db(tmp_path: Path) -> None:
    feed = make_feed(tmp_path=tmp_path)
    crawled = list(feed.crawl())
    assert len(crawled) == 100

    exclude = lambda bs: b'00' in bs
    feed = make_feed(tmp_path=tmp_path, exclude_raw=exclude)
    pruned = feed.prune_db(dry=True)
    assert pruned == 10

    pruned = feed.prune_db()
    assert pruned == 10

    feed = make_feed(tmp_path=tmp_path)
    items = list(feed.feed())
    assert len(items) == 90


def test_search_excludes(tmp_path: Path) -> None:
    """
    If exclude is defined, search should respect it
    """
    exclude = lambda bs: b'00' in bs
    feed = make_feed(tmp_path=tmp_path, exclude_raw=exclude)
    results = list(feed.search_all(limit=None))
    assert len(results) == 90


def test_exclude_updated(tmp_path: Path) -> None:
    """
    If exclude is defined after initial crawling, nexttime we request feed, it should be respected
    """
    feed = make_feed(tmp_path=tmp_path)
    results = list(feed.search_all(limit=None))
    assert len(results) == 100

    list(feed._insert(results, dry=False))

    d = feed.asdict()
    assert len(d) == 100

    # scenario: we crawled some stuff and then updated exclude query
    def exclude(o: Json) -> bool:
        return '9' in o['text']

    feed2 = make_feed(tmp_path=tmp_path, exclude=exclude)
    d = feed2.asdict()
    assert len(d) == 81


def test_exclude_error(tmp_path: Path) -> None:
    """
    Make sure things work properly if exclude function fails for some reason
    """
    triggered_error = False

    def exclude_1(data: bytes) -> bool:
        # trigger a random error
        if b'item 011' in data:
            nonlocal triggered_error
            triggered_error = True
            raise RuntimeError
        return b'item 08' in data

    feed = make_feed(tmp_path=tmp_path, exclude_raw=exclude_1)
    results = list(feed.crawl())
    assert triggered_error
    triggered_error = False  # reset
    # despite the error, everything else should be processed properly
    assert len(results) == 90
    assert '011' in feed.asdict()

    def exclude_2(data: bytes) -> bool:
        # trigger a random error
        if b'item 091' in data:
            nonlocal triggered_error
            triggered_error = True
            raise RuntimeError
        return b'item 01' in data

    feed = make_feed(tmp_path=tmp_path, exclude_raw=exclude_2)
    d = feed.asdict()
    assert triggered_error
    triggered_error = False  # reset
    assert len(d) == 80
    assert '091' in d

    pruned = feed.prune_db()
    assert triggered_error
    triggered_error = False  # reset
    assert pruned == 10


@dataclass
class ErrorFeed(BaseFeed):
    PREFIX = 'errors'
    QueryCls = str

    def parse(self, data: bytes):
        x = int(data.decode('utf8'))
        if x % 10 == 9:
            raise RuntimeError('Simulating parsing error')
        return x

    @property
    def search(self) -> SearchF:
        def _search(query: SearchQuery, *, limit: int | None):
            for i in range(1, 100):
                uid = str(i)
                data = uid.encode('utf8')
                yield uid, data

        return _search


def test_parse_errors(tmp_path: Path) -> None:
    feed = ErrorFeed.make(
        query_name='testing',
        queries=[Query('whatever')],
        db_path=tmp_path / 'test.sqlite',
    )

    crawled = [x for x in feed.crawl() if not isinstance(x, Exception)]
    assert len(crawled) == 99

    errors = [o for _, uid, o in crawled if isinstance(o, Exception)]
    assert len(errors) == 10

    # make sure items are present in the db despite the errors during parsing
    db_items = [(uid, x) for _, uid, x in feed._select_all()]
    assert db_items == sorted([(str(i), str(i).encode('utf8')) for i in range(1, 100)])
