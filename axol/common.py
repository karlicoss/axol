import logging
import re
from typing import Any, Callable, List, Sequence, Type, TypeVar
from typing_extensions import Protocol


from kython.klogging import LazyLogger


def setup_paths() -> None:
    import sys
    sys.path.extend([
        '/L/coding/tentacle',
        '/L/coding/spinboard',
        '/L/coding/reach',
    ])
setup_paths()

logger = LazyLogger('axol', level=logging.DEBUG)



Filter = Any

class Query(Protocol):
    searcher: Type[Any]
    queries: List[str]
    excluded: Sequence[Filter]
    @property
    def repo_name(self) -> str: ...



# TODO move somewhere more appropriate
def slugify(s: str):
    s = s.strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)
