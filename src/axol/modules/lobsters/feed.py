from dataclasses import dataclass
from pathlib import Path

from axol.core.feed import Feed as BaseFeed, SearchF

from . import model, query


@dataclass
class Feed(BaseFeed[model.Result]):
    PREFIX = 'lobsters'
    QueryType = query.Query

    def parse(self, data: bytes) -> model.Result:
        return model.parse(data)

    @property
    def search(self) -> SearchF:
        from . import search

        return search.search


def test_feed(tmp_path: Path) -> None:
    import dataclasses
    import datetime
    import os
    import pytest

    if 'CI' in os.environ:
        pytest.skip('skipping to prevent potentially hammering the website')

    feed = Feed.make(
        query_name='test_lobsters',
        queries=[query.Query('scoped tagging')],
        db_path=tmp_path / 'test.sqlite',
    )
    crawled = list(feed.crawl())
    assert len(crawled) > 20

    items = list(feed.feed())
    assert len(items) == len(crawled)

    # just a random story that should be present
    [(uid, dt, s)] = [(uid, dt, x) for uid, dt, x in items if isinstance(x, model.Story) and x.author == 'jado']
    assert s.score > 40
    assert s.comments > 15
    # replace volatile attributes
    s = dataclasses.replace(s, score=0, comments=0)
    assert s == model.Story(
        dt=datetime.datetime(2024, 4, 24, 11, 37, 55, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400))),
        id='mutdyp',
        title='Borrow checking, RC, GC, and the Eleven (!) Other Memory Safety Approaches',
        url='https://verdagon.dev/grimoire/grimoire',
        author='jado',
        score=0,
        comments=0,
        tags=['programming'],
    )

    # just a random comment that should be present
    [(uid, dt, c)] = [(uid, dt, x) for uid, dt, x in items if isinstance(x, model.Comment) and x.author == 'englishm']
    assert 'My thought process' in c.text
    assert 'this type of content' in c.text
    c = dataclasses.replace(c, text='')
    assert c == model.Comment(
        dt=datetime.datetime(2015, 1, 29, 10, 55, 39, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=64800))),
        id='c_8tqeri',
        title='They Live',
        url='/s/fm4zlm/they_live',
        author='englishm',
        score=1,
        text='',
    )