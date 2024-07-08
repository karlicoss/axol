from dataclasses import dataclass

from axol.core.feed import Feed as BaseFeed, SearchF

from . import model, query


@dataclass
class Feed(BaseFeed):
    PREFIX = 'reddit'
    QueryType = query.Query

    def parse(self, data: bytes):
        return model.parse(data)

    @property
    def search(self) -> SearchF:
        from . import search

        return search.search
