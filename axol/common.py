from kython.klogging import LazyLogger

import logging

def setup_paths():
    import sys
    sys.path.extend([
        '/L/coding/tentacle',
        '/L/coding/spinboard',
        '/L/coding/reach',
    ])

logger = LazyLogger('axol')
def get_logger():
    return logger

# TODO kython??
class classproperty(object):
    def __init__(self, f):
        self.f = f
    def __get__(self, obj, owner):
        return self.f(owner)



# TODO move target separately?
class ForSpinboard:
    @classproperty
    def Target(cls):
        from spinboard import Result # type: ignore
        return Result

class ForReach:
    @classproperty
    def Target(cls):
        from reach import Result # type: ignore
        return Result

class ForTentacle:
    @classproperty
    def Target(cls):
        from tentacle import Result # type: ignore
        return Result
