from dataclasses import dataclass
from pathlib import Path

from axol.core.feed import Feed as BaseFeed
from axol.core.feed import SearchF
from axol.core.query import raw

from . import markdown, model, query


@dataclass
class Feed(BaseFeed[model.Model, query.Query]):
    PREFIX = 'github'
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
    from datetime import UTC, datetime

    import pytest

    if 'CI' in os.environ:
        pytest.skip('skipping to prevent potentially hammering the website')

    feed = Feed.make(
        query_name='test',
        # Limit to issues: repository search is too small to exercise pagination,
        # while commit/code search is much slower and more prone to GitHub rate limiting.
        queries=[query.Query('statistical outlier detection', included=['issues'])],
        db_path=tmp_path / 'test.sqlite',
    )
    # GitHub search pages contain 100 items, so use >2 pages to exercise pagination.
    crawled = list(feed.crawl(limit=250))
    assert len(crawled) >= 250

    items = list(feed.feed())
    assert len(items) == len(crawled)

    for _dt, uid, o in items:
        assert not isinstance(o, Exception), (uid, o)
        assert isinstance(o, model.Issue), (uid, o)
        assert o.html_url.startswith('https://github.com/'), o
        assert '/' in o.repo, o
        assert len(o.title) > 0, o

    [o] = [o for _, uid, o in items if uid == 'issue_1193622005']
    assert isinstance(o, model.Issue)
    assert o.body is not None
    assert 'CRDB-13544' in o.body
    o = dataclasses.replace(o, body='')
    assert o == model.Issue(
        created_at=datetime(2022, 4, 5, 19, 27, tzinfo=UTC),
        html_url='https://github.com/cockroachdb/cockroach/issues/79451',
        user=model.User(login='matthewtodd', url='https://github.com/matthewtodd'),
        repo='cockroachdb/cockroach',
        title='outliers: configurable statistical detection per fingerprint',
        body='',
    )

    repo_feed = Feed.make(
        query_name='test_repo',
        # Keep repository search covered with a narrow query so it stays cheap.
        queries=[query.Query(raw('axol user:karlicoss'), included=['repositories'])],
        db_path=tmp_path / 'test_repo.sqlite',
    )
    repo_crawled = list(repo_feed.crawl(limit=5))
    assert len(repo_crawled) == 1

    repo_items = list(repo_feed.feed())
    [repo] = [o for _, uid, o in repo_items if uid == 'repo_karlicoss_axol']
    assert isinstance(repo, model.Repository)
    assert repo.stars > 1  # can be flaky
    repo = dataclasses.replace(repo, stars=-1)
    assert repo == model.Repository(
        created_at=datetime(2020, 3, 10, 23, 50, 25, tzinfo=UTC),
        html_url='https://github.com/karlicoss/axol',
        user=model.User(login='karlicoss', url='https://github.com/karlicoss'),
        repo='karlicoss/axol',
        description='Personal news feed: search for results on Reddit/Pinboard/Twitter/Hackernews and read as RSS',
        topics=(),
        stars=-1,
    )
