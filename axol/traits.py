from pathlib import Path
from typing import Optional, Type

from kython import classproperty

from axol.trait import AbsTrait, pull

from config import ignored_reddit


# TODO move target separately?
class ForSpinboard:
    @classproperty
    def Target(cls):
        # pylint: disable=import-error
        from spinboard import Result # type: ignore
        return Result

class ForReach:
    @classproperty
    def Target(cls):
        # pylint: disable=import-error
        from reach import Result # type: ignore
        return Result

class ForTentacle:
    @classproperty
    def Target(cls):
        # pylint: disable=import-error
        from tentacle import Result # type: ignore
        return Result

IgnoreRes = Optional[str]

class IgnoreTrait(AbsTrait):
    @classmethod
    def ignore(trait, obj, *args, **kwargs) -> IgnoreRes:
        raise NotImplementedError
ignore_result = pull(IgnoreTrait.ignore)


# TODO default impl?? not sure..
class SpinboardIgnore(ForSpinboard, IgnoreTrait):
    @classmethod
    def ignore(trait, obj, *args, **kwargs) -> IgnoreRes:
        # if obj.user in ('lvwrence', 'ma51ne64'):
        #     return 'user blacklisted'
        return None
        # return obj.user == 'lvwrence' # TODO FIXME NOCOMMIT

class TentacleIgnore(ForTentacle, IgnoreTrait):
    @classmethod
    def ignore(trait, obj, *args, **kwargs) -> IgnoreRes:
        return None

class ReachIgnore(ForReach, IgnoreTrait):
    @classmethod
    def ignore(trait, obj, *args, **kwargs) -> IgnoreRes:
        # TODO eh, I def. need to separate in different files; that way I can have proper autocompletion..
        return ignored_reddit(obj)
IgnoreTrait.reg(SpinboardIgnore, TentacleIgnore, ReachIgnore)



# TODO maybe, return For directly?
def get_result_type(repo: Path) -> Type:
    name = repo.name
    # TODO this could also be a trait?
    if name.startswith('reddit'):
        # pylint: disable=import-error
        from reach import Result # type: ignore
        return Result
    elif name.startswith('github'):
        # pylint: disable=import-error
        from tentacle import Result # type: ignore
        return Result
    else:
        # pylint: disable=import-error
        from spinboard import Result # type: ignore
        return Result
