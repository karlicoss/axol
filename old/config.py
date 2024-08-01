from pathlib import Path
import re
from typing import List, Iterator, NamedTuple, Type, Any, Sequence

from axol.common import Query, slugify
from axol.queries import GithubQ, pinboard_quote, RedditQ, TwitterQ, PinboardQ, HackernewsQ, filter_queries

from more_itertools import flatten

BASE_DIR = Path(__file__).absolute().parent; assert BASE_DIR.exists()
# TODO come up with better names?
DATABASES   = BASE_DIR / 'databases'
RESULTS     = DATABASES # TODO deprecate 'databases'?
REPORTS_DIR = BASE_DIR / 'reports'

from private_config import *

# TODO later just remove config from version control?

def pintag(query: str) -> str:
    # https://pinboard.in/howto/#tags
    if ' ' in query or ':' in query:
        raise RuntimeError(f'Bad tag: {query}')
    return f'tag:{query}'


def gen_pintags(query: str) -> List[str]:
    # TODO crap! it's also very useful to just concatenate the words in tag...
    return list(set(map(pintag, [
        query.replace(" ", "-"),
        query.replace(" ", "_"),
    ])))


class Subreddit(NamedTuple):
    regex: str

    def matches(self, item) -> bool:
        return re.fullmatch(self.regex, item.subreddit, re.I) is not None

    @property
    def reason(self) -> str:
        return f'subreddit {self.regex}'

class Contains(NamedTuple):
    seq: str

    def matches(self, item) -> bool:
        xx = f'{item.title} {item.description} {item.subreddit}'.lower()
        return self.seq in xx

    @property
    def reason(self) -> str:
        return f'contains {self.seq}'


sub = Subreddit

def subreddit(*subs):
    return [Subreddit(s) for s in subs]

def contains(*items):
    return [Contains(i) for i in items]


pintags_implicit = object()

def Dummy(*args, **kwargs):
    return None


def E(x): # 'exact'
    return f'"{x}"'

# PinboardQ = Dummy # TODO till I fix the (apparently) banned host issue
# RedditQ = Dummy
# GithubQ = Dummy

# true for pintags means generating from queries
def qall(qname: str, *args, pintags=None) -> Iterator[Query]:
    if pintags is None:
        pintags = [pintags_implicit]

    ptags: List[str] = []
    for p in pintags:
        if p is pintags_implicit:
            ptags.extend(flatten([gen_pintags(q) for q in args]))
        else:
            # TODO ignore if it's already pintag??
            assert isinstance(p, str)
            ptags.append(pintag(p))
    ptags = list(sorted(set(ptags)))

    yield RedditQ(qname, *args)
    yield PinboardQ(qname, *args, *ptags)
    yield GithubQ(qname, *args)
    # TODO FIXME twitter
    # TODO FIXME hackernews
    # eh, doesn't work on Algolia: "personal knowledge" OR "personal information"

def EXCLUDED_SUBREDDITS():
    return [
        # TODO just exclude globablly?
        subreddit(
            'airsoft', 'mw4', 'CombatFootage',
            'stalker', 'airsoftmarket',
            'insurgency', 'MilitaryPorn',
            'ProjectMilSim', 'RingOfElysium', 'GunPorn',
            'EscapefromTarkov', 'joinsquad', 'dayz',
            'ClearBackblast', 'syriancivilwar',
            'gaming', 'u_tkaqnfkf1',
            'friendsafari', 'GlobalPowers', 'TheSilphRoad',
            'LoLeventVoDs',
            '.*pokemon.*', '.*nintendo.*', '.*pkmn.*',
            '.*gameboy.*',
            '.*gun.*',
            'callofduty', '.*warfare.*',
            'nfl', 'hockey', 'PunSpecialForces',
            'PunSpecialForces',
            'combinedarms',
            'dayrsurvival',
            'The_Donald',
            'leagueoflegends',
            'arma',
            'nfa',
            'wargame',
            '.*conspiracy.*',
            '.*weapons.*',
            '.*firearms.*',
            '.*military.*',
        ),
        contains('pokemon', 'ak47', ' guns '),
    ]

# TODO warn if we got less than expected?
def make_queries() -> Iterator[Query]:
    P = PinboardQ
    R = RedditQ
    G = GithubQ
    T = TwitterQ
    H = HackernewsQ

    yield from qall(
        'bret victor',
        'bret victor',
    )
    # TODO FIXME merge queries after that? not sure..

    yield from qall(
        'arbtt',
        'arbtt',
    )

    if True:
        emind = 'extended mind'
        yield from qall(
            emind,
            emind,
        )
        yield T(
            emind,
            f'"{emind}"',
        )
        yield H(
            emind,
            f'"{emind}"',
        )

    if True:
        ll = 'lifelogging'
        yield from qall(
            ll,
            ll,
            pintags=[pintags_implicit, 'lifelog']
        )
        yield T(
            ll,
            ll,
        )
        yield H(
            ll,
            ll,
        )

    openbci = 'openbci'
    yield from qall(
        openbci,
        openbci,
        pintags=[pintags_implicit, 'bci'],
    )
    yield H(openbci, openbci)

    # TODO not sue about eeg? where to put it?

    if True:
        pk = 'pkm'
        pkm = 'personal knowledge management'
        yield R(
            pk,
            'pkm', pkm,
            excluded=EXCLUDED_SUBREDDITS(),
        )
        yield P(
            pk,
            'pkm', pintag('pkm'),
            pkm  , *gen_pintags(pkm),
            pintag('km'), pintag('pim'),
        )
        yield G(
            pk, # TODO shit. that's a bit messed up...
            'pkm NOT pokemon', # TODO NOT pkm
            f'"{pkm}"',
            quote=False,
        )
        yield T(
            pk,
            f'"{pkm}"',
        )
        yield H(
            pk,
            f'"personal knowledge"',
            # TODO FIXME use "personal knowledge" everywhere?
            # TODO FIXME use 'personal information'??
        )

    qg = 'quantum gravity' # TODO eh, needs quoting?
    yield from qall(
        qg,
        qg,
    )

    if True:
        qs = 'quantified self'
        yield from qall(
            qs,
            qs, 'quantified-self',
            pintags=[pintags_implicit, 'quantifiedself'],
        )
        yield T(
            qs,
            '"quantified self"',
        )
        yield H(
            qs,
            '"quantified self"',
        )

    ###
    tc = 'ted chiang'
    yield from qall(tc,   tc, pintags=['tedchiang'])
    yield         T(tc, E(tc))
    yield         H(tc, E(tc))
    ###

    ###
    egan = 'greg egan'
    yield from qall(egan,   egan, pintags=['gregegan'])
    yield         T(egan, E(egan))
    yield         H(egan, E(egan))
    ###

    ###
    if True:
        ar = 'argonov'
        yield from qall(
            ar,
            'виктор аргонов', # TODO eh, needs quoting?
        )
        yield T(ar, '"виктор аргонов"')
    ###

    ###
    sr = 'spaced repetition'
    yield from qall(sr,   sr)
    yield         H(sr, E(sr))
    ###

    ###
    sa = 'scott alexander'
    if True:
        # too much stuff from pinboard... maybe keep github? 
        # yield from qall(sa, sa, pintags=['scottalexander'])
        yield H(sa, E(sa))
    ###

    bb = 'beepb00p.xyz'
    # TODO FIXME ugh. how to make qall nicer to use??
    # TODO FIXME make sure qall and these oneoff things don't overlap
    yield R(bb, bb, 'domain:' + bb)
    yield P(bb, bb)
    yield G(bb, bb, 'code:' + bb, 'issues:' + bb)
    yield T(bb, bb)
    yield H(bb, bb)

    mypy = 'mypy'
    yield from qall(
        mypy,
        mypy,
        pintags=['mypy'],
    )
    # yield T(mypy, mypy) # TODO not sure about twitter..
    yield H(mypy, mypy)


    ###
    memex = 'memex'
    yield from qall(
        memex,
        memex,
        pintags=[memex],
    )
    yield T(memex, memex)
    yield H(memex, memex)
    ###

    ###
    kedr = 'kedr livanskiy'
    yield from qall(kedr,   kedr )
   #mm, twitter is quite spammy.. https://twitter.com/search?q=kedr%20livanskiy&f=live
   #yield         T(kedr, E(kedr))
    yield         H(kedr, E(kedr))
    ###

    ###
    exobrain = 'exobrain'
    yield from qall(exobrain, exobrain, pintags=[exobrain])
    yield         T(exobrain, exobrain)
    yield         H(exobrain, exobrain)
    ###

    ###
    hotz = 'george hotz'
    yield from qall(hotz,   hotz )
    yield         T(hotz, E(hotz))
    yield         H(hotz, E(hotz))
    ###


    ###
    ghk = 'github.com/karlicoss'
    yield from qall(ghk, ghk)
    yield         T(ghk, ghk)
    yield         H(ghk, ghk)
    ### 


    del P
    del R
    del G
    del T
    del H

def get_queries(include=None, exclude=None, name=None):
    queries = list(filter(lambda x: x is not None, make_queries()))
    return filter_queries(queries, include=include, exclude=exclude, name=name)


# TODO get rid of this later...
from functools import lru_cache
@lru_cache(1)
def get_reddit_queries():
    res = []
    for q in get_queries():
        if not isinstance(q, RedditQ):
            continue
        res.append(q)
    return res

from typing import Optional
def ignored_reddit(item) -> Optional[str]:
    for q in get_reddit_queries():
        # TODO eh. might need a quicker way to ignore....
        for ex in q.excluded:
            # TODO the item itself knows how to match
            if ex.matches(item):
                return ex.reason
    return None


if __name__ == '__main__':
    for q in get_queries():
    # just check that it doesn't crash
        print(q)
