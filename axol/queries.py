from typing import Sequence

from kython import flatten

from .common import Query, slugify, Filter
# TODO Filter needs to be a more flexible type...

def pinboard_quote(s: str):
    # shit, single quotes do not work right with pinboard..
    if s.startswith('tag:'):
        return s
    if s.startswith("'"):
        return s
    return f'"{s}"'



class GithubQ(Query):
    @property
    def searcher(self):
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
        self.excluded = flatten(excluded)

    @property
    def repo_name(self) -> str:
        return self.sname + '_' + slugify(self.qname)

    def __repr__(self):
        return str(self.__dict__)
