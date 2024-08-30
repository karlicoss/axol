# NOTE: some info on search operators here https://lobste.rs/search
# TODO title: could be useful?
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

from typing_extensions import assert_never

from axol.core.query import Compilable, _check, doublequote, exact, raw

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
                case raw(q):
                    yield SearchQuery(query=q, kind=kind)
                case exact(q) | str(q):
                    yield SearchQuery(query=doublequote(_check(q)), kind=kind)
                case _:
                    assert_never(query)
