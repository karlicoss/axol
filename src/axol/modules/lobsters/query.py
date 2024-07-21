# NOTE: some info on search operators here https://lobste.rs/search
# however e.g. double quotes don't work
# TODO title: could be useful?
from dataclasses import dataclass
from typing import Iterator, Literal, assert_never

from axol.core.query import exact, raw, Compilable


Kind = Literal[
    'stories',
    'comments',
]


@dataclass
class SearchQuery:
    query: str
    kind: Kind


@dataclass
class Query(Compilable[SearchQuery]):
    # NOTE: looks like on lobsters search is always exact?
    # anywyay, double quotes result in zero results
    # reported here https://github.com/lobsters/lobsters/issues/1296
    # NOTE: search query for lobsters seems to match text behind the link
    # TODO lobsters also has tags? although a very small set of predefined ones
    query: str | raw | exact
    kind: Kind | None = None

    def compile(self) -> Iterator[SearchQuery]:
        query = self.query
        kind = self.kind
        kinds: list[Kind] = ['stories', 'comments'] if kind is None else [kind]
        for kind in kinds:
            match query:
                case raw(q) | exact(q) | str(q):
                    yield SearchQuery(query=q, kind=kind)
                case _:
                    assert_never(query)
