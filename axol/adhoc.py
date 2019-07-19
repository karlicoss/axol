from pathlib import Path
from typing import Sequence

from axol.common import Query, slugify
from axol.crawl import process_query


def run(queries: Sequence[str], sources: Sequence[str], tdir: Path):
    [src] = sources
    assert src == 'github'

    q = GithubQ(src, *queries)

    dry = False
    process_query(q, path=tdir, dry=dry)

    print(type(tdir))
    pass


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

    @property
    def sname(self):
        return 'github'

    def __init__(self, qname: str, *queries: str, quote=True):
        if len(queries) == 1 and isinstance(queries[0], list):
            queries = queries[0] # TODO ugh.
        self.qname = qname
        if quote:
            # TODO ???
            self.queries = list(map(pinboard_quote, queries))
        else:
            self.queries = list(queries)
    # TODO how to make it unique and fs safe??

    @property
    def repo_name(self) -> str:
        return f'github_{slugify(self.qname)}'

    def __repr__(self):
        return str(self.__dict__)
