import logging
from typing import Any, List, Sequence, Type

from kython.klogging import LazyLogger
from typing_extensions import Protocol


def setup_paths():
    import sys
    sys.path.extend([
        '/L/coding/tentacle',
        '/L/coding/spinboard',
        '/L/coding/reach',
    ])
setup_paths()

logger = LazyLogger('axol', level=logging.DEBUG)

# TODO kython??
class classproperty(object):
    def __init__(self, f):
        self.f = f
    def __get__(self, obj, owner):
        return self.f(owner)


Filter = Any

class Query(Protocol):
    searcher: Type[Any]
    queries: List[str]
    excluded: Sequence[Filter]
    @property
    def repo_name(self): str = ...
