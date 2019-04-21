from pathlib import Path
import re
from typing import List, Iterator, NamedTuple, Type, Any, Sequence
from typing_extensions import Protocol

from kython import flatten

OUTPUTS = Path(__file__).parent.joinpath('outputs').resolve()

assert OUTPUTS.exists()

# TODO move somewhere more appropriate
def slugify(s: str):
    s = s.strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)


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


def pinboard_quote(s: str):
    # shit, single quotes do not work right with pinboard..
    if s.startswith('tag:'):
        return s
    if s.startswith("'"):
        return s
    return f'"{s}"'


Filter = Any

class Query(Protocol):
    searcher: Type[Any]
    queries: List[str]
    excluded: Sequence[Filter]
    @property
    def repo_name(self): str = ...


class GithubQ(Query):
    @property
    def searcher(self):
        from tentacle import Tentacle # type: ignore
        return Tentacle

    @property
    def sname(self):
        return 'github'

    def __init__(self, qname: str, *queries: str, quote=True):
        if len(queries) == 1 and isinstance(queries[0], list):
            queries = queries[0] # TODO ugh.
        self.qname = qname
        if quote:
            self.queries = list(map(pinboard_quote, queries))
        else:
            self.queries = list(queries)
    # TODO how to make it unique and fs safe??

    @property
    def repo_name(self) -> str:
        return f'github_{slugify(self.qname)}'

    def __repr__(self):
        return str(self.__dict__)

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

# TODO Filter needs to be a more flexible type...

class RedditQ(Query):
    @property
    def searcher(self):
        from reach import Reach # type: ignore
        return Reach

    @property
    def sname(self):
        return 'reddit'

    def __init__(self, qname: str, *queries: str, excluded: Sequence[Filter]=()) -> None:
        if len(queries) == 1 and isinstance(queries[0], list):
            queries = queries[0] # TODO ugh.
        self.qname = qname
        self.queries = list(map(pinboard_quote, queries))
        self.excluded = flatten(excluded)

    @property
    def repo_name(self) -> str:
        return f'reddit_' + slugify(self.qname)

    def __repr__(self):
        return str(self.__dict__)

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


# TODO warn if we got less than expected?
def make_queries() -> Iterator[Query]:
    P = PinboardQ
    R = RedditQ
    G = GithubQ

    yield from qall(
        'arbtt',
        'arbtt',
    )

    emind = 'extended mind'
    yield from qall(
        emind,
        emind,
    )

    ll = 'lifelogging'
    yield from qall(
        ll,
        ll,
        pintags=[pintags_implicit, 'lifelog']
    )

    openbci = 'openbci'
    yield from qall(
        openbci,
        openbci,
        pintags=[pintags_implicit, 'bci'],
    )

    # TODO not sue about eeg? where to put it?

    pkm = 'personal knowledge management'
    yield R(
        'pkm',
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
        'pkm',
        'pkm', pintag('pkm'),
        pkm  , *gen_pintags(pkm),
        pintag('km'), pintag('pim'),
    )
    yield G(
        'pkm', # TODO shit. that's a bit messed up...
        'pkm NOT pokemon', # TODO NOT pkm
        f'"{pkm}"',
        quote=False,
    )

    qg = 'quantum gravity'
    yield from qall(
        qg,
        qg,
    )

    qs = 'quantified self'
    yield from qall(
        qs,
        qs, 'quantified-self',
        pintags=[pintags_implicit, 'quantifiedself'],
    )

    # TODO probably, no github?
    tc = 'ted chiang'
    yield from qall(
        tc,
        tc,
        pintags=['tedchiang'],
    )

    yield from qall(
        'argonov',
        'виктор аргонов',
    )

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
