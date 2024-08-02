from dataclasses import dataclass
from pathlib import Path

from axol.core.feed import Feed as BaseFeed, SearchF

from . import model, query, markdown


@dataclass
class Feed(BaseFeed[model.Model, query.Query]):
    PREFIX = 'hackernews'
    QueryCls = query.Query

    def parse(self, data: bytes) -> model.Model:
        return model.parse(data)

    @property
    def search(self) -> SearchF:
        from . import search

        return search.search

    MarkdownAdapter = markdown.MarkdownAdapter


def test_feed(tmp_path: Path) -> None:
    from datetime import datetime, timezone
    import os
    import pytest

    if 'CI' in os.environ:
        pytest.skip('skipping to prevent potentially hammering the website')

    feed = Feed.make(
        query_name='test_hn',
        queries=[query.Query('unexpected return')],
        db_path=tmp_path / 'test.sqlite',
    )
    crawled = [x for x in feed.crawl() if not isinstance(x, Exception)]

    assert len(crawled) > 10

    # random comment that should be present
    [(c, uid)] = [(c, uid) for dt, uid, c in crawled if isinstance(c, model.Comment) and c.id == '10097990']
    assert uid == '10097990'
    assert c.author == 'barrkel'
    assert c.created_at == datetime(2015, 8, 21, 15, 9, 54, tzinfo=timezone.utc)
    assert 'interacting with the outside world' in c.text.html

    [(s, uid)] = [(s, uid) for dt, uid, s in crawled if isinstance(s, model.Story) and s.id == '29223181']
    assert uid == '29223181'
    assert s.author == 'walterbell'
    assert s.points > 100
    assert s.num_comments > 200
    assert s.title == 'Corded headphones are making an unexpected return'
    assert s.url == 'https://www.wsj.com/articles/are-airpods-out-why-cool-kids-are-wearing-wired-headphones-11636753407'
