from datetime import datetime
from typing import Any, Type, TypeVar

Json = dict[str, Any]

Uid = str

CrawlResult = tuple[Uid, Json]

datetime_aware = datetime


T = TypeVar('T')
def _check(x: Any, t: Type[T]) -> T:
    assert isinstance(x, t), x
    return x
