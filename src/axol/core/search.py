from typing import Iterator, Protocol, Sequence

from .common import SearchResult


class SearchF(Protocol):
    def __call__(self, *, query: str, limit: int | None) -> Iterator[SearchResult]:
        pass


def search_all(
    *,
    search_function: SearchF,
    queries: Sequence[str],
    limit: int | None,
) -> Iterator[SearchResult]:
    handled = set()
    for query in queries:
        for uid, j in search_function(query=query, limit=limit):
            if uid in handled:
                continue
            handled.add(uid)
            # todo could yield query here?
            yield uid, j
