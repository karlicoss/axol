from dataclasses import dataclass
from typing import assert_never, Iterator

from axol.core.query import exact, raw, doublequote, _check, Compilable


@dataclass
class SearchQuery:
    query: str


# FIXME would be nice to ensure query module isn't needed for sarching/crawling
@dataclass
class Query(Compilable[SearchQuery]):
    # NOTE: normal search also matches strings inside urls
    # NOTE: doesn't support 'or'
    # NOTE: looks like you can precede a word with - to exclude from query?
    query: str | raw | exact

    def compile(self) -> Iterator[SearchQuery]:
        query = self.query
        match query:
            case raw(q):
                yield SearchQuery(query=q)
            case exact(q) | str(q):
                # NOTE: when in quotes, search is still case independent
                # NOTE: when quoted, still does some fuzzly-ish stuff
                #       e.g. for "bret victor" matches "Bret-Victor" or "bret_victor"
                # NOTE: for hn, definitely makes sense to make it exact search by default
                #       e.g.
                #       - search(bret victor) matches "Don't Bet Your Future on Specialized Vector Databases"
                #       - search(PIM) matches pimp
                yield SearchQuery(query=doublequote(_check(q)))
            case _:
                assert_never(query)
