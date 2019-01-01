from kython import flatten

import re
from typing import List, Iterator, NamedTuple, Type, Any
from typing_extensions import Protocol

# TODO move somewhere more appropriate
def slugify(s: str):
    s = s.strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)


def pintag(query: str) -> List[str]:
    # https://pinboard.in/howto/#tags
    return list({
        f'tag:{query.replace(" ", "-")}',
        f'tag:{query.replace(" ", "_")}',
# TODO crap! it's also very useful to just concatenate the words in tag...
    })


def pinboard_quote(s: str):
    # shit, single quotes do not work right with pinboard..
    if s.startswith('tag:'):
        return s
    if s.startswith("'"):
        return s
    return f'"{s}"'

class Query(Protocol):
    searcher: Type[Any]
    queries: List[str]
    @property
    def repo_name(self): str = ...

class GithubQ(Query):
    @property
    def searcher(self):
        from tentacle import Tentacle # type: ignore
        return Tentacle

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


class RedditQ(Query):
    @property
    def searcher(self):
        from reach import Reach # type: ignore
        return Reach

    def __init__(self, qname: str, *queries: str) -> None:
        if len(queries) == 1 and isinstance(queries[0], list):
            queries = queries[0] # TODO ugh.
        self.qname = qname
        self.queries = list(map(pinboard_quote, queries))

    @property
    def repo_name(self) -> str:
        return f'reddit_' + slugify(self.qname)

    def __repr__(self):
        return str(self.__dict__)

# true for pintags means generating from queries
def qall(qname: str, *args, pintags=None) -> Iterator[Query]:
    if pintags is None:
        pintags = []
    if pintags is True:
        pintags = flatten([pintag(q) for q in args])
    pintags = list(sorted(set(pintags)))

    yield RedditQ(qname, *args)
    yield PinboardQ(qname, *args, *pintags)
    yield GithubQ(qname, *args)


# TODO warn if we got less than expected?
def make_queries() -> Iterator[Query]:
    P = PinboardQ
    R = RedditQ
    G = GithubQ

    yield from qall('arbtt', 'arbtt')

    emind = 'extended mind'
    yield from qall(
        emind,
        emind,
        pintags=True,
    )

    ll = 'lifelogging'
    yield from qall(
        ll,
        ll,
        pintags=True,
    )

    openbci = 'openbci'
    yield from qall(
        openbci,
        openbci,
        pintags=True,
    ) #TODO maybe True by default??

    pkm = 'personal knowledge management'
    yield R(
        'pkm',
        'pkm', pkm
    )
    yield P(
        'pkm',
        'pkm', *pintag('pkm'),
        pkm  , *pintag(pkm),
    )
    yield G(
        'pkm',
        'pkm NOT pokemon',
        f'"{pkm}"',
        quote=False,
    )

    return
    yield from qall(
        'pkm',
        pkm, 'pkm',
        pintags=True
    )

    qg = 'quantum gravity'
    yield from qall(
        qg,
        qg,
        pintags=True,
    )

    qs = 'quantified self'
    yield from qall(
        qs,
        qs, 'quantified-self',
        pintags=True, # TODO if query is empty, imply from name??
    )

    # TODO probably, no github?
    tc = 'ted chiang'
    yield from qall(
        tc,
        tc,
        pintags=pintag('tedchiang'),
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
        pintags=pintag('scottalexander')
    )
    del P
    del R
    del G

queries = make_queries()
