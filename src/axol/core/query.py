from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from more_itertools import unique_everseen


@dataclass
class exact:
    query: str


@dataclass
class raw:
    query: str


# double quote
def doublequote(query: str) -> str:
    return '"' + query + '"'


def _check(s: str) -> str:
    # TODO check no special characters at all?
    assert '"' not in s, s
    assert "'" not in s, s
    return s


class Compilable[T](Protocol):
    def compile(self) -> Iterator[T]: ...


def compile_queries[Compiled](queries: Sequence[Compilable[Compiled]]) -> Iterator[Compiled]:
    def it() -> Iterator[Compiled]:
        for query in queries:
            yield from query.compile()

    return unique_everseen(it())
