import logging
import re
from itertools import islice
from typing import Any, Callable, List, Sequence, Type, TypeVar, Iterable, Iterator
from typing_extensions import Protocol


from kython.klogging import LazyLogger


def setup_paths() -> None:
    from pathlib import Path
    d = Path(__file__).absolute().parent.parent
    import sys
    sys.path.extend([
        str(d / 'tentacle_repo' ),
        str(d / 'spinboard_repo'),
        str(d / 'reach_repo'    ),
    ])
setup_paths()

logger = LazyLogger('axol', level=logging.INFO)



Filter = Any

class Query(Protocol):
    searcher: Type[Any]
    queries: List[str] # TODO FIXME assert on empty list?
    excluded: Sequence[Filter]
    @property
    def repo_name(self) -> str: ...



# TODO move somewhere more appropriate
def slugify(s: str):
    s = s.strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)



T = TypeVar('T')


def ichunks(l: Iterable[T], n: int) -> Iterator[List[T]]:
    it: Iterator[T] = iter(l)
    while True:
        chunk: List[T] = list(islice(it, 0, n))
        if len(chunk) == 0:
            break
        yield chunk
