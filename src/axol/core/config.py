from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

from .common import Json, SearchResults


Query = str  # TODO common?


@dataclass
class Config:
    queries: Sequence[Query]
    db_path: Path | str  # FIXME derive from crawler/repo 'name'?

    @abstractmethod
    def parse(self, j: Json):
        # TODO not sure about this.. also kinda annoying it erases the type..
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str) -> SearchResults:
        # FIXME maybe doesn't need to accept queries??
        raise NotImplementedError


@dataclass
class HnConfig(Config):
    def parse(self, j: Json):
        import axol.modules.hackernews.model as M
        return M.parse(j)

    def search(self, query: str) -> SearchResults:
        import axol.modules.hackernews.search as M
        return M.search(query)


@dataclass
class RedditConfig(Config):
    def parse(self, j: Json):
        import axol.modules.reddit.model as M
        return M.parse(j)

    def search(self, query: str) -> SearchResults:
        import axol.modules.reddit.search as M
        return M.search(query)


def configs() -> Iterator[Config]:
    config_hn = HnConfig(
        queries=(
            # TODO duplicate query is a good test!
            'karlicoss',  # FIXME this query returns too many false positives for fuzzy match...
            'karlicoss',
            # 'beepb00p.xyz',
        ),
        db_path='hn.sqlite',
    )
    yield config_hn
    config_reddit = RedditConfig(
        queries=(
            'beepb00p.xyz',
        ),
        db_path='reddit.sqlite',
    )
    yield config_reddit
