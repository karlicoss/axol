from dataclasses import dataclass
from pathlib import Path

from axol.core.feed import Feed as BaseFeed
from axol.core.feed import SearchF

from . import markdown, model, query


@dataclass
class Feed(BaseFeed[model.Model, query.Query]):
    PREFIX = 'reddit'
    QueryCls = query.Query

    def parse(self, data: bytes) -> model.Model:
        return model.parse(data)

    @property
    def search(self) -> SearchF:
        from . import search

        return search.search

    MarkdownAdapter = markdown.MarkdownAdapter


def test_feed(tmp_path: Path) -> None:
    import dataclasses
    import os
    from datetime import datetime, timezone

    import pytest

    if 'CI' in os.environ:
        pytest.skip('skipping to prevent potentially hammering the website')

    feed = Feed.make(
        query_name='test',
        queries=[query.Query('catamorphism')],
        db_path=tmp_path / 'test.sqlite',
    )
    crawled = list(feed.crawl())
    assert len(crawled) > 50

    items = list(feed.feed())

    [o] = [o for dt, uid, o in items if isinstance(o, model.Submission) and uid == 'u1t237']

    assert o.ups > 20  # fuzzy since it's changing
    assert 'the day you learn what a catamorphism is, is an enlightening day' in o.selftext_md
    o = dataclasses.replace(
        o,
        ups=-1,
        downs=-1,
        selftext_md='',
        selftext_html='',  # TODO make it return html and check?
    )
    assert o == model.Submission(
        id='u1t237',
        created_at=datetime(2022, 4, 12, 7, 9, 21, tzinfo=timezone.utc),
        subreddit_name='haskell',
        author_name='Axman6',
        downs=-1,
        ups=-1,
        _permalink='/r/haskell/comments/u1t237/the_visitor_pattern_and_catamorphisms/',
        title='The visitor pattern and catamorphisms',
        url='https://www.reddit.com/r/haskell/comments/u1t237/the_visitor_pattern_and_catamorphisms/',
        selftext_md='',
        selftext_html='',
    )
