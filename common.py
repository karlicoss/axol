import logging

def setup_paths():
    import sys
    sys.path.extend([
        '/L/coding/tentacle',
        '/L/coding/spinboard',
        '/L/coding/reach',
    ])

def get_logger():
    return logging.getLogger('axol')

# TODO kython??
class classproperty(object):
    def __init__(self, f):
        self.f = f
    def __get__(self, obj, owner):
        return self.f(owner)
