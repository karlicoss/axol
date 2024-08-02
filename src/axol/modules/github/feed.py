from dataclasses import dataclass
from pathlib import Path

from axol.core.feed import Feed as BaseFeed, SearchF

from . import model, query, markdown


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
    import datetime
    import os
    import pytest

    if 'CI' in os.environ:
        pytest.skip('skipping to prevent potentially hammering the website')

    feed = Feed.make(
        query_name='test',
        queries=[query.Query('statistical outlier detection')],
        db_path=tmp_path / 'test.sqlite',
    )
    crawled = list(feed.crawl())
    assert len(crawled) > 500

    items = list(feed.feed())
    assert len(items) > 500

    # test some random objects
    [o] = [o for _, uid, o in items if uid == 'commit_52cbaf3b5063bad7456b782b4f36f12278dc70ab']
    assert o == model.Commit(
        created_at=datetime.datetime(2024, 4, 20, 14, 57, 27, tzinfo=datetime.timezone(datetime.timedelta(seconds=32400))),
        html_url='https://github.com/dmurooka/data-wrangling/commit/52cbaf3b5063bad7456b782b4f36f12278dc70ab',
        user=model.User(login='dmurooka', url='https://github.com/dmurooka'),
        repo='dmurooka/data-wrangling',
        message='Demonstrate Statistical Outlier Detection - IQR',
    )

    [o] = [o for _, uid, o in items if uid == 'repo_abdullahsaka_Outlier_Detection']
    assert isinstance(o, model.Repository)
    assert o.stars > 1  # can be flaky
    o = dataclasses.replace(o, stars=-1)
    assert o == model.Repository(
        created_at=datetime.datetime(2019, 9, 10, 6, 42, 28, tzinfo=datetime.timezone.utc),
        html_url='https://github.com/abdullahsaka/Outlier_Detection',
        user=model.User(login='abdullahsaka', url='https://github.com/abdullahsaka'),
        repo='abdullahsaka/Outlier_Detection',
        description='Undergraduate Project - Statistical Outlier Detection Methods',
        topics=('anomaly-detection-algorithm', 'outlier-detection', 'statistics', 'z-score'),
        stars=-1,
    )

    [o] = [o for _, uid, o in items if uid == 'issue_691845851']
    assert isinstance(o, model.Issue)
    assert o.body is not None
    assert 'One simple method is the Hampel filtering' in o.body
    o = dataclasses.replace(o, body='')
    assert o == model.Issue(
        created_at=datetime.datetime(2020, 9, 3, 10, 25, 1, tzinfo=datetime.timezone.utc),
        html_url='https://github.com/scipy/scipy/issues/12809',
        user=model.User(login='jerabaul29', url='https://github.com/jerabaul29'),
        repo='scipy/scipy',
        title='ENH: ndimage/signal: add Hampel filter',
        body='',
    )
