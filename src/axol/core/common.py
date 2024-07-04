from datetime import datetime
from typing import Any, Iterator, Type, TypeVar

Json = dict[str, Any]

Uid = str

datetime_aware = datetime

SearchResult = tuple[Uid, Json]
SearchResults = Iterator[SearchResult]

DbResult = tuple[Uid, datetime_aware, Json]


T = TypeVar('T')


def _check(x: Any, t: Type[T]) -> T:
    assert isinstance(x, t), x
    return x


def notnone(x: T | None) -> T:
    assert x is not None
    return x


def json_copy(j: Json) -> Json:
    if isinstance(j, (int, bool, str, float, type(None))):
        return j
    if isinstance(j, list):
        return [json_copy(x) for x in j]
    if isinstance(j, dict):
        return {k: json_copy(v) for k, v in j.items()}
    raise RuntimeError(j, type(j))
