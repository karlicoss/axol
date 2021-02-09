from typing import Sequence

from .common import Query, slugify, Filter
# TODO Filter needs to be a more flexible type...

from more_itertools import flatten

def pinboard_quote(s: str):
    # shit, single quotes do not work right with pinboard..
    # TODO meeeeh
    # TODO FIXME set of allowed prefixes?
    if s.startswith('tag:'):
        return s
    if s.startswith('domain:'):
        return s
    if any(s.startswith(c) for c in ('issues:', 'code:')):
        # TODO FIMXE need to quote second part???
        return s
    # TODO only quote if it's got whitespace? not even sure about that...
    if s.startswith("'") or s.startswith('"'):
        return s
    return f'"{s}"'



class GithubQ(Query):
    @property
    def searcher(self):
        # TODO eh. don't think it's good API
        from tentacle import Tentacle # type: ignore
        return Tentacle

    @property # TODO cproperty?
    def sname(self):
        return 'github'

    def __init__(self, qname: str, *queries: str, quote=True):
        if len(queries) == 1 and isinstance(queries[0], list):
            queries = queries[0] # TODO ugh.
        self.qname = qname
        if quote:
            # TODO why pinboard_quote???
            self.queries = list(map(pinboard_quote, queries))
        else:
            self.queries = list(queries)
    # TODO how to make it unique and fs safe??

    # TODO reuse sname??
    @property
    def repo_name(self) -> str:
        return self.sname + '_' + slugify(self.qname)

    def __repr__(self):
        return str(self.__dict__)



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
        self.excluded = list(flatten(excluded))

    @property
    def repo_name(self) -> str:
        return self.sname + '_' + slugify(self.qname)

    def __repr__(self):
        return str(self.__dict__)


class TwitterQ(Query):
    @property
    def searcher(self):
        from .twitter import TwitterSearch
        return TwitterSearch

    @property
    def sname(self):
        return 'twitter'

    def __init__(self, qname: str, query: str): # TODO FIXME multiple
        self.qname = qname
        self.queries = list(map(pinboard_quote, [query]))

    @property
    def repo_name(self) -> str:
        return self.sname + '_' + slugify(self.qname)

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
        return self.sname + '_' + slugify(self.qname)

    def __repr__(self):
        return str(self.__dict__)

class BaseQuery(Query):
    def __init__(self, qname: str, query: str): # TODO FIXME multiple
        self.qname = qname
        self.queries = list(map(pinboard_quote, [query]))

    @property
    def repo_name(self) -> str:
        return self.sname + '_' + slugify(self.qname)

    def __repr__(self):
        return str(self.__dict__)


class HackernewsQ(BaseQuery):
    @property
    def searcher(self):
        from .hackernews import HackernewsSearch
        return HackernewsSearch

    @property
    def sname(self):
        # TODO FIXME make it a variable?
        return 'hackernews'



# convenient to temporary ignore certain providers via returning None
def filter_queries(queries, include=None, exclude=None, name=None):
    if include is not None and exclude is not None:
        raise RuntimeError('please specify only one of include/exclude')
    if include is not None:
        queries = [q for q in queries if q.sname in include]
    if exclude is not None:
        queries = [q for q in queries if q.sname not in exclude]
    if name is not None:
        queries = [q for q in queries if q.qname == name]
    return queries
