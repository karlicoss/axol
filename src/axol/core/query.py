from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

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


Compiled_co = TypeVar('Compiled_co', covariant=True)


class Compilable(Protocol[Compiled_co]):
    def compile(self) -> Iterator[Compiled_co]: ...


def compile_queries(queries: Sequence[Compilable[Compiled_co]]) -> Iterator[Compiled_co]:
    def it() -> Iterator[Compiled_co]:
        for query in queries:
            yield from query.compile()

    return unique_everseen(it())
