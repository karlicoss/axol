from dataclasses import dataclass
from pathlib import Path

from axol.core.common import html
from axol.core.feed import Feed as BaseFeed, SearchF

from . import model, query


@dataclass
class Feed(BaseFeed[model.Result, query.Query]):
    PREFIX = 'lobsters'
    QueryCls = query.Query

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
    [(dt, uid, s)] = [(dt, uid, x) for dt, uid, x in items if isinstance(x, model.Story) and x.author == 'jado']
    assert uid == 'mutdyp'
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
        permalink='https://lobste.rs/s/mutdyp/borrow_checking_rc_gc_eleven_other_memory',
        score=0,
        comments=0,
        tags=['programming'],
    )

    # just a random comment that should be present
    [(dt, uid, c)] = [(dt, uid, x) for dt, uid, x in items if isinstance(x, model.Comment) and x.author == 'englishm']
    assert uid == 'c_8tqeri'
    assert 'My thought process' in c.text.html
    assert 'this type of content' in c.text.html
    c = dataclasses.replace(c, text=html(''))
    assert c == model.Comment(
        dt=datetime.datetime(2015, 1, 29, 10, 55, 39, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=64800))),
        id='c_8tqeri',
        title='They Live',
        url='https://lobste.rs/s/fm4zlm/they_live',
        author='englishm',
        permalink='https://lobste.rs/s/fm4zlm/they_live#c_8tqeri',
        score=1,
        text=html(''),
    )
