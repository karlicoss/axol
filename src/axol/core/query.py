from dataclasses import dataclass
from typing import Iterator, Protocol, Sequence, TypeVar

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


Compiled = TypeVar('Compiled', covariant=True)


class Compilable(Protocol[Compiled]):
    def compile(self) -> Iterator[Compiled]: ...


def compile_queries(queries: Sequence[Compilable[Compiled]]) -> Iterator[Compiled]:
    def it() -> Iterator[Compiled]:
        for query in queries:
            yield from query.compile()

    return unique_everseen(it())
