# knows how to jsonify each specific query?
# this is a bit nicer -- kinda like mixins but dynamic.. so the code doesn't have to interleave with fetchers
from datetime import datetime
from typing import Any, Dict, Type

from kython.kjson import Json, ToFromJson

from axol.common import classproperty
from axol.traits import ForSpinboard
from axol.trait import AbsTrait, pull


# class JsonTrait(AbsTrait):
#     _impls = {}

#     @classmethod
#     def to_json(trait, obj) -> Json:
#         raise NotImplementedError

#     # @classmethod
#     # def from_json(trait, jj: Json):
#     #     raise NotImplementedError
# # from_json = # TODO ugh.. sometimes might require manual dispatching??

# class SpinboardJson(JsonTrait):
#     # TODO rename Target to Self?
#     @classproperty
#     def Target(trait):
#         from spinboard import Result # type: ignore
#         return Result


# to_json = pull(JsonTrait.to_json)

class JsonTrait(AbsTrait): # TODO generic..
    @classmethod
    def from_json(trait, obj: Json):
        raise NotImplementedError


class SpinboardJsonTrait(ForSpinboard, JsonTrait):
    @classmethod
    def from_json(trait, obj: Json):
        cp = {k: v for k, v in obj.items()}
        cp['when'] = datetime.strptime(cp['when'], '%Y%m%d%H%M%S')
        return trait.Target(**cp)


class Jsoner:
    def __init__(self) -> None:
        self.to_json_f: Dict[Type, Any] = {}
        self.from_json_f: Dict[Type, Any] = {}

    def to_json(self, obj) -> Json:
        return self.to_json_f[type(obj)](obj)

    def from_json(self, cls, jj: Json):
        return self.from_json_f[cls](jj)

_jsoner = Jsoner() # eh, hopefully singleton is ok..

def from_json(cls, jj: Json):
    return _jsoner.from_json(cls, jj)


def to_json(thing) -> Json:
    return _jsoner.to_json(thing)

def register_spinboard():
    from spinboard import Result # type: ignore

    # TODO switch to tofromjson..
    def _to(obj) -> Json:
        res = obj._asdict()
        res['when'] = res['when'].strftime('%Y%m%d%H%M%S')

        # make sure it's inverse
        tmp = _from(res)
        assert tmp == obj

        return res


    _jsoner.to_json_f[Result] = _to
    JsonTrait.reg(SpinboardJsonTrait)

def register_reach():
    from reach import Result # type: ignore

    tf = ToFromJson(
        Result,
        as_dates=['when'],
    )
    _jsoner.to_json_f[Result] = lambda r: tf.to(r)
    _jsoner.from_json_f[Result] = lambda j: tf.from_(j)

def register_tentacle():
    from tentacle import Result # type: ignore

    tf = ToFromJson(
        Result,
        as_dates=['when'],
    )
    _jsoner.to_json_f[Result] = lambda r: tf.to(r)
    _jsoner.from_json_f[Result] = lambda j: tf.from_(j)


def register_all():
    for r in [
            register_spinboard,
            register_reach,
            register_tentacle,
    ]:
        try:
            r()
        except Exception as e:
            raise e # TODO not sure what should we do...

register_all() # TODO ??? 
