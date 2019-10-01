from pathlib import Path
import re
from typing import List, Iterator, NamedTuple, Type, Any, Sequence

from kython import flatten

from axol.common import Query, slugify
from axol.queries import GithubQ, pinboard_quote, RedditQ, TwitterQ

BASE_DIR = Path(__file__).absolute().parent; assert BASE_DIR.exists()
OUTPUTS = BASE_DIR / 'outputs'

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


# TODO protocol?..
class PinboardQ(Query):
    @property
    def searcher(self):
        from spinboard import Spinboard # type: ignore
        return Spinboard

    @property
    def sname(self):
        return 'pinboard'

    def __init__(self, name: str, *queries: str, quote=True):
        if len(queries) == 1 and isinstance(queries[0], list):
            queries = queries[0] # TODO ugh.
        self.name = name
        if quote:
            self.queries = list(map(pinboard_quote, queries))
        else:
            self.queries = list(queries)
    # TODO how to make it unique and fs safe??

    @property
    def repo_name(self) -> str:
        # TODO 'pinboard' prefix? slugify??
        return self.name

    def __repr__(self):
        return str(self.__dict__)


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


# TODO warn if we got less than expected?
def make_queries() -> Iterator[Query]:
    P = PinboardQ
    R = RedditQ
    G = GithubQ
    T = TwitterQ

    yield from qall(
        'bret victor',
        'bret victor',
    )

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

    openbci = 'openbci'
    yield from qall(
        openbci,
        openbci,
        pintags=[pintags_implicit, 'bci'],
    )

    # TODO not sue about eeg? where to put it?

    if True:
        pk = 'pkm'
        pkm = 'personal knowledge management'
        yield R(
            pk,
            'pkm', pkm,
            excluded=[
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
                    '.*pokemon.*', '.*nintendo.*', '.*gun.*',
                ),
                contains('pokemon', 'ak47', ' guns '),
            ],
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

    # TODO probably, no github?
    tc = 'ted chiang'
    yield from qall(
        tc,
        tc,
        pintags=['tedchiang'],
    )

    if True:
        ar = 'argonov'
        yield from qall(
            ar,
            'виктор аргонов', # TODO eh, needs quoting?
        )
        yield T(ar, '"виктор аргонов"')

    sr = 'spaced repetition'
    yield from qall(
        sr,
        sr,
    )

    sa = 'scott alexander'
    yield from qall(
        sa,
        sa,
        pintags=['scottalexander'],
    )
    del P
    del R
    del G
    del T

# convenient to temporary ignore certain providers via returning None
def get_queries(include=None, exclude=None):
    queries = list(filter(lambda x: x is not None, make_queries()))
    if include is not None and exclude is not None:
        raise RuntimeError('please specify only one of include/exclude')
    if include is not None:
        queries = [q for q in queries if q.sname in include]
    if exclude is not None:
        queries = [q for q in queries if q.sname not in exclude]
    return queries


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
