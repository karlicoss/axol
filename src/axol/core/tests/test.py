from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from axol.core.common import Json
from axol.core.config import Config as BaseConfig, SearchF, ExcludeP


@dataclass
class SearchQuery:
    query: str


@dataclass
class Query:
    query: str

    def compile(self) -> Iterator[SearchQuery]:
        yield SearchQuery(query=self.query)


@dataclass
class DummyConfig(BaseConfig):
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


def make_config(*, tmp_path: Path, exclude: ExcludeP | None = None) -> DummyConfig:
    return DummyConfig.make(
        query_name='testing',
        queries=[Query('whatever')],
        db_path=tmp_path / 'test.sqlite',
        exclude=exclude,
    )


def test_search_excludes(tmp_path: Path) -> None:
    exclude = lambda bs: b'0000' in bs
    config = make_config(tmp_path=tmp_path, exclude=exclude)
    results = list(config.search_all(limit=None))
    assert len(results) == 90


def test_exclude_updated(tmp_path: Path) -> None:
    config = make_config(tmp_path=tmp_path)
    results = list(config.search_all(limit=None))
    assert len(results) == 100

    config.insert(results)

    def asdict(config: DummyConfig):
        d = {}
        # FIXME implement feed helper?...
        for uid, crawl_dt, j in config.select_all():
            assert uid not in d  # just in case
            d[uid] = j
        return d

    d = asdict(config=config)
    assert len(d) == 100

    # scenario: we crawled some stuff and then updated exclude query
    exclude = lambda bs: b'9' in bs
    config2 = make_config(tmp_path=tmp_path, exclude=exclude)
    d = asdict(config=config2)
    assert len(d) == 81
