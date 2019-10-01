from .common import Query, slugify

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
            # TODO why pinboard_quote???
            self.queries = list(map(pinboard_quote, queries))
        else:
            self.queries = list(queries)
    # TODO how to make it unique and fs safe??

    # TODO reuse sname??
    @property
    def repo_name(self) -> str:
        return f'github_{slugify(self.qname)}'

    def __repr__(self):
        return str(self.__dict__)
