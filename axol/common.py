from kython.klogging import LazyLogger

import logging

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
