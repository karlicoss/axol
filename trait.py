from typing import Dict, Type, Dict


# TODO mm, that should only be stored in target trait!!!
class AbsTrait:
    Target: Type = NotImplemented

    # TODO how to refer to target here??
    _impls: Dict[Type, Type['AbsTrait']] = NotImplemented

    @classmethod
    def reg(cls, tr: Type['AbsTrait']):
        cls._impls[tr.Target] = tr # TODO check for existence?

    @classmethod
    def for_(cls, f):
        if not isinstance(f, type):
            f = type(f)
        return cls._impls[f]

def pull(mref):
    Trait = mref.__self__
    name = mref.__name__
    def _m(obj, *args, **kwargs):
        Dispatched = Trait.for_(obj)
        return getattr(Dispatched, name)(obj, *args, **kwargs)
    return _m
