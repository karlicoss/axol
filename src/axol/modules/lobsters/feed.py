from dataclasses import dataclass

from axol.core.feed import Feed as BaseFeed, SearchF

from . import model, query


@dataclass
class Feed(BaseFeed[model.Result]):
    PREFIX = 'lobsters'
    QueryType = query.Query

    def parse(self, data: bytes) -> model.Result:
        return model.parse(data)

    @property
    def search(self) -> SearchF:
        from . import search

        return search.search
