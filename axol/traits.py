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

class ForTwitter:
    @classproperty
    def Target(cls):
        from axol.twitter import Result
        return Result


IgnoreRes = Optional[str]

class IgnoreTrait(AbsTrait):
    @classmethod
    def ignore_group(trait, objs) -> IgnoreRes:
        ignores = [trait.ignore(o) for _, o in objs]
        ignores = [x for x in ignores if x is not None]
        if len(ignores) == 0:
            return None
        else:
            return '|'.join(ignores) # meh


    @classmethod
    def ignore(trait, obj, *args, **kwargs) -> IgnoreRes:
        return None
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
    pass

class ReachIgnore(ForReach, IgnoreTrait):
    @classmethod
    def ignore(trait, obj, *args, **kwargs) -> IgnoreRes:
        # TODO eh, I def. need to separate in different files; that way I can have proper autocompletion..
        return ignored_reddit(obj)

class TwitterIgnore(ForTwitter, IgnoreTrait):
    pass

IgnoreTrait.reg(SpinboardIgnore, TentacleIgnore, ReachIgnore, TwitterIgnore)



# TODO maybe, return For directly?
# TODO FIXME duplication with queries..
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
        return Result # TODO FIXME reuse 'For' here??  or just get marker by name directly?
    else:
        # pylint: disable=import-error
        from spinboard import Result # type: ignore
        return Result
