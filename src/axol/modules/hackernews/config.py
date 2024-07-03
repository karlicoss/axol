from dataclasses import dataclass

from axol.core.common import Json
from axol.core.config import Config as BaseConfig, SearchF

from . import model, query


@dataclass
class Config(BaseConfig[model.Result]):
    PREFIX = 'hackernews'
    QueryType = query.Query

    def parse(self, j: Json) -> model.Result:
        return model.parse(j)

    @property
    def search(self) -> SearchF:
        from . import search

        return search.search
