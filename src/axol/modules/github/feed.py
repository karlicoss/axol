from dataclasses import dataclass

from axol.core.common import Json
from axol.core.feed import Feed as BaseFeed, SearchF

from . import model, query


@dataclass
class Feed(BaseFeed):
    PREFIX = 'github'
    QueryType = query.Query

    def parse(self, j: Json):
        return model.parse(j)

    @property
    def search(self) -> SearchF:
        from . import search

        return search.search
