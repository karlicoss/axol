from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import orjson

from axol.core.common import Json, Uid
from axol.core.feed import Feed as BaseFeed, SearchF, ExcludeP


@dataclass
class SearchQuery:
    query: str


@dataclass
class Query:
    query: str

    def compile(self) -> Iterator[SearchQuery]:
        yield SearchQuery(query=self.query)


@dataclass
class DummyFeed(BaseFeed):
    PREFIX = 'dummy'
    QueryType = str

    def parse(self, data: bytes):
        return orjson.loads(data)

    @property
    def search(self) -> SearchF:
        def _search(query: SearchQuery, *, limit: int | None):
            for i in range(100):
                uid = f'{i:05d}'
                j = {'text': f'item {uid}'}
                yield uid, orjson.dumps(j)

        return _search


def make_feed(*, tmp_path: Path, exclude: ExcludeP | None = None) -> DummyFeed:
    return DummyFeed.make(
        query_name='testing',
        queries=[Query('whatever')],
        db_path=tmp_path / 'test.sqlite',
        exclude=exclude,
    )


def test_crawl(tmp_path: Path) -> None:
    feed = make_feed(tmp_path=tmp_path)
    crawled = list(feed.crawl())
    assert len(crawled) == 100

    data = list(feed.feed())
    assert len(data) == 100


def test_prune(tmp_path: Path) -> None:
    feed = make_feed(tmp_path=tmp_path)
    crawled = list(feed.crawl())
    assert len(crawled) == 100

    exclude = lambda bs: b'0000' in bs
    feed = make_feed(tmp_path=tmp_path, exclude=exclude)
    pruned = feed.prune_db(dry=True)
    assert pruned == 10

    pruned = feed.prune_db()
    assert pruned == 10

    feed = make_feed(tmp_path=tmp_path)
    items = list(feed.feed())
    assert len(items) == 90


def test_search_excludes(tmp_path: Path) -> None:
    exclude = lambda bs: b'0000' in bs
    feed = make_feed(tmp_path=tmp_path, exclude=exclude)
    results = list(feed.search_all(limit=None))
    assert len(results) == 90


def test_exclude_updated(tmp_path: Path) -> None:
    feed = make_feed(tmp_path=tmp_path)
    results = list(feed.search_all(limit=None))
    assert len(results) == 100

    list(feed._insert(results, dry=False))

    def asdict(feed: DummyFeed) -> dict[Uid, Json]:
        d: dict[Uid, Json] = {}
        for crawl_dt, uid, o in feed.feed():
            assert uid not in d  # just in case
            assert not isinstance(o, Exception)
            d[uid] = o
        return d

    d = asdict(feed=feed)
    assert len(d) == 100

    # scenario: we crawled some stuff and then updated exclude query
    exclude = lambda bs: b'9' in bs
    feed2 = make_feed(tmp_path=tmp_path, exclude=exclude)
    d = asdict(feed=feed2)
    assert len(d) == 81


@dataclass
class ErrorFeed(BaseFeed):
    PREFIX = 'errors'
    QueryType = str

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


def test_errors(tmp_path: Path) -> None:
    feed = ErrorFeed.make(
        query_name='testing',
        queries=[Query('whatever')],
        db_path=tmp_path / 'test.sqlite',
    )

    crawled = list(feed.crawl())
    assert len(crawled) == 99

    errors = [o for _, uid, o in crawled if isinstance(o, Exception)]
    assert len(errors) == 10

    # make sure items are present in the db despite the errors during parsing
    db_items = [(uid, x) for _, uid, x in feed._select_all()]
    assert db_items == sorted([(str(i), str(i).encode('utf8')) for i in range(1, 100)])
