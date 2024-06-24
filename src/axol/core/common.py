from datetime import datetime
from typing import Any, Iterator, Type, TypeVar

Json = dict[str, Any]

Uid = str

SearchResult = tuple[Uid, Json]
SearchResults = Iterator[SearchResult]

datetime_aware = datetime


T = TypeVar('T')
def _check(x: Any, t: Type[T]) -> T:
    assert isinstance(x, t), x
    return x
