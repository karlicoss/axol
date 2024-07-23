from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any, Iterator, NewType, Type, TypeVar

Json = dict[str, Any]

Uid = NewType('Uid', str)


def make_uid(s: str) -> Uid:
    assert isinstance(s, str), s
    # limit characters to prevent stupid crap like spaces etc
    assert re.fullmatch(r'[\w\.-]+', s), s
    # kinda arbitrary, but feels like it's worth limiting length
    assert 0 < len(s) < 80, s
    return Uid(s)


datetime_aware = datetime

SearchResult = tuple[Uid, bytes]
SearchResults = Iterator[SearchResult]


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


@dataclass
class html:
    "Marker class to signal that the object contains raw html"
    html: str
