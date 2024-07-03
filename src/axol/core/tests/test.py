from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

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

    def parse(self, j: Json):
        return j

    @property
    def search(self) -> SearchF:
        def _search(query: SearchQuery, *, limit: int | None):
            for i in range(100):
                uid = f'{i:05d}'
                yield uid, {'text': f'item {uid}'}

        return _search


def make_feed(*, tmp_path: Path, exclude: ExcludeP | None = None) -> DummyFeed:
    return DummyFeed.make(
        query_name='testing',
        queries=[Query('whatever')],
        db_path=tmp_path / 'test.sqlite',
        exclude=exclude,
    )


def test_search_excludes(tmp_path: Path) -> None:
    exclude = lambda bs: b'0000' in bs
    feed = make_feed(tmp_path=tmp_path, exclude=exclude)
    results = list(feed.search_all(limit=None))
    assert len(results) == 90


def test_exclude_updated(tmp_path: Path) -> None:
    feed = make_feed(tmp_path=tmp_path)
    results = list(feed.search_all(limit=None))
    assert len(results) == 100

    feed.insert(results)

    def asdict(feed: DummyFeed):
        d: dict[Uid, Json] = {}
        for uid, crawl_dt, o in feed.feed():
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
