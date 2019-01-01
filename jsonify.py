# knows how to jsonify each specific query?
# this is a bit nicer -- kinda like mixins but dynamic.. so the code doesn't have to interleave with fetchers
from datetime import datetime
from kython.kjson import ToFromJson

from typing import Any, Dict, Type

Json = Any

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

    def _from(jdict: Json):
        cp = {k: v for k, v in jdict.items()}
        cp['when'] = datetime.strptime(cp['when'], '%Y%m%d%H%M%S')
        return Result(**cp)

    # TODO switch to tofromjson..
    def _to(obj) -> Json:
        res = obj._asdict()
        res['when'] = res['when'].strftime('%Y%m%d%H%M%S')

        # make sure it's inverse
        tmp = _from(res)
        assert tmp == obj

        return res


    _jsoner.to_json_f[Result] = _to
    _jsoner.from_json_f[Result] = _from

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

register_all()
