from dataclasses import dataclass
from pathlib import Path

from axol.core.feed import Feed as BaseFeed
from axol.core.feed import SearchF

from . import markdown, model, query


@dataclass
class Feed(BaseFeed[model.Model, query.Query]):
    PREFIX = 'pinboard'
    QueryCls = query.Query

    def parse(self, data: bytes) -> model.Model:
        return model.parse(data)

    @property
    def search(self) -> SearchF:
        from . import search

        return search.search

    MarkdownAdapter = markdown.MarkdownAdapter


def test(tmp_path: Path) -> None:
    import os
    from datetime import datetime, timezone

    import pytest

    if 'CI' in os.environ:
        pytest.skip('skipping to prevent potentially hammering the website')

    feed = Feed.make(
        query_name='test',
        # FIXME ugh, looks like tag search now needs to be behind the login???
        queries=[query.Query('of present day', kind='regular')],
        db_path=tmp_path / 'test.sqlite',
    )
    crawled = list(feed.crawl())
    assert len(crawled) > 60

    items = list(feed.feed())
    assert len(items) > 60

    [o] = [o for dt, uid, o in items if not isinstance(o, Exception) and uid == '08d0a5f0eacd']
    assert o.slug == '08d0a5f0eacd'
    assert o.created_at == datetime(2017, 12, 29, 21, 39, 36, tzinfo=timezone.utc)
    assert o.author == 'robertogreco'
    assert o.title == 'West Portal - FoundSF'
    assert o.url == 'http://www.foundsf.org/index.php?title=West_Portal'
    assert {'history', 'construction'} - set(o.tags) == set()  # no exact check in case tags change
    assert o.description is not None
    assert 'The first neighborhoods to be developed, St Francis Woo' in o.description
