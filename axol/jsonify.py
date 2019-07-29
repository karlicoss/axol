# knows how to jsonify each specific query?
# this is a bit nicer -- kinda like mixins but dynamic.. so the code doesn't have to interleave with fetchers
from datetime import datetime
from typing import Type

from kython import classproperty
from kython.kjson import Json, ToFromJson

from axol.traits import ForSpinboard, ForReach, ForTentacle, ForTwitter
from axol.trait import AbsTrait, pull

# TODO rename Target to Self?
class JsonTrait(AbsTrait): # TODO generic..
    @classproperty
    def tofrom(trait):
        return ToFromJson( # TODO FIXME isoformat??
            trait.Target,
            as_dates=['when'],
        )

    @classmethod
    def from_json(trait, obj: Json):
        return trait.tofrom.from_(obj)

    @classmethod
    def to_json(trait, item):
        res = trait.tofrom.to(item)
        # make sure it's inverse
        assert item == trait.from_json(res)
        return res
to_json = pull(JsonTrait.to_json)


class SpinboardJsonTrait(ForSpinboard, JsonTrait):
    pass

class ReachJsonTrait(ForReach, JsonTrait):
    pass

class TentacleJsonTrait(ForTentacle, JsonTrait):
    pass

class TwitterJsonTrait(ForTwitter, JsonTrait):
    pass

JsonTrait.reg(SpinboardJsonTrait, ReachJsonTrait, TentacleJsonTrait, TwitterJsonTrait)
