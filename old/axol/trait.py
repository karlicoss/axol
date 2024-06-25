from typing import Dict, Type, Dict, Any

from .core.common import classproperty


# TODO mm, that should only be stored in target trait!!!
class AbsTrait:
    Target: Type = NotImplemented

    @classproperty
    # TODO how to refer to target here??
    def _impls(cls) -> Dict[Type, Type['AbsTrait']]:
        kk = '_type2impls'
        if not hasattr(cls, kk):
            setattr(cls, kk, {})
        return getattr(cls, kk)


    @classmethod
    def reg(cls, *traits: Type['AbsTrait']) -> None:
        for tr in traits:
            cls._impls[tr.Target] = tr # TODO check for existence?

    @classmethod
    def for_(cls, f): # TODO returns AbsTrait??
        if not isinstance(f, type): # TODO eh?
            f = type(f)
        return cls._impls[f]

def pull2(Trait, name):
    def _m(obj, *args, **kwargs):
        Dispatched = Trait.for_(obj)
        return getattr(Dispatched, name)(obj, *args, **kwargs)
    return _m


def pull(mref):
    Trait = mref.__self__
    name = mref.__name__
    return pull2(Trait, name)



# https://stackoverflow.com/a/3655857/706389
def islambda(v: Any) -> bool:
    LAMBDA = lambda:0
    return isinstance(v, type(LAMBDA)) and v.__name__ == LAMBDA.__name__


class _For:
    def __getitem__(self, cls) -> Type:
        class ForCls:
            @classproperty # TODO can be static prop?
            def Target(ccc, cls=cls):
                if islambda(cls):
                    cc = cls()
                else:
                    cc = cls
                return cc
        return ForCls

For = _For()


def test():
    from typing import NamedTuple
    class A:
        x = 123

    class B:
        z = "string!"

    class L:
        x = 'smth lazy'


    class ShowTrait(AbsTrait):
        @classmethod
        def show(trait, obj, *args, **kwargs):
            raise NotImplementedError

        def safe_int(self):
            raise NotImplementedError

    # TODO shit. so why does it work with classmethod, but not normal methods??
    show = pull(ShowTrait.show)
    # TODO this is kinda ok, but should be nice. Maybe even repetition is better than string..
    safe_int = pull2(ShowTrait, 'safe_int')

    class ForA:
        @classproperty
        def Target(cls):
            return A

    class ShowA(ForA, ShowTrait):
        @classmethod
        def show(trait, obj, *args, **kwargs):
            return f'A containing {obj.x}'

        def safe_int(obj):
            return obj.x


    # TODO perhaps specify what it's for in square brackets?
    # although no, too restrictive
    # TODO better error messages? Might do with abc module
    class ShowB(For[B], ShowTrait):
        @classmethod
        def show(trait, obj, *args, **kwargs):
            return f'I am {obj.z}'

        def safe_int(obj):
            return None

    ForL = For[lambda: L] # TODO eh, capturing?
    class ShowL(ForL, ShowTrait):
        @classmethod
        def show(trait, obj, *args, **kwargs):
            return 'showl'

        def safe_int(obj):
            return None

    ShowTrait.reg(ShowA, ShowB, ShowL)


    assert show(A()) == 'A containing 123'
    assert show(B()) == 'I am string!'
    assert show(L()) == 'showl'

    aa = A()
    ll = L()
    assert show(aa) == 'A containing 123'
    assert show(B()) == 'I am string!'
    assert show(ll) == 'showl'

    assert safe_int(aa) == 123
    assert safe_int(ll) == None
