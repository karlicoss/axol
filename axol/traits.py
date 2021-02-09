from pathlib import Path
from typing import Optional, Type

from .trait import AbsTrait, pull
from .core.common import classproperty, the

from config import ignored_reddit


# TODO move target separately?
class ForSpinboard:
    name = 'pinboard'

    @classproperty
    def Target(cls):
        # pylint: disable=import-error
        from spinboard import Result # type: ignore
        return Result

class ForReach:
    name = 'reddit'

    @classproperty
    def Target(cls):
        # pylint: disable=import-error
        from reach import Result # type: ignore
        return Result

class ForTentacle:
    name = 'github'

    @classproperty
    def Target(cls):
        # pylint: disable=import-error
        from tentacle import Result # type: ignore
        return Result

class ForTwitter:
    name = 'twitter'

    @classproperty
    def Target(cls):
        from .twitter import Result
        return Result


class ForHackernews:
    name = 'hackernews'

    @classproperty
    def Target(cls):
        from .hackernews import Result
        return Result


Fors = [ForSpinboard, ForReach, ForTentacle, ForTwitter, ForHackernews]

def For(res):
    return the([F for F in Fors if res == F.Target])

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

# TODO FIXME default impls?
class TwitterIgnore(ForTwitter, IgnoreTrait):
    pass

class HackernewsIgnore(ForHackernews, IgnoreTrait):
    pass

# TODO FIXME could register at the time of inheritance?
IgnoreTrait.reg(SpinboardIgnore, TentacleIgnore, ReachIgnore, TwitterIgnore, HackernewsIgnore)



# TODO maybe, return For directly?
# TODO FIXME duplication with queries..
def get_result_type(repo: Path) -> Type:
    name = repo.name
    # TODO this could also be a trait?
    if name.startswith('reddit'):
        return ForReach.Target
    elif name.startswith('github'):
        return ForTentacle.Target
    elif name.startswith('twitter'):
        return ForTwitter.Target
    elif name.startswith('hackernews'):
        return ForHackernews.Target # TODO meh..
    elif name.startswith('pinboard'):
        return ForSpinboard.Target
    else:
        # TODO remove this?
        return ForSpinboard.Target
