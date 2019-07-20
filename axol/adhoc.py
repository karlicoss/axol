from pathlib import Path
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import Sequence

from kython.tui import getch

from axol.common import Query, slugify, logger
from axol.crawl import process_query
from axol.report import do_repo



def do_run(queries: Sequence[str], sources: Sequence[str], tdir: Path):
    [src] = sources
    assert src == 'github'
    qname = src

    q = GithubQ(qname, *queries)

    dry = False
    process_query(q, path=tdir, dry=dry)

    repo = tdir / ('github_' + qname) # TODO FIXME need to return it from process?
    for d in ('summary', 'rendered'):
        (tdir / d).mkdir(exist_ok=True, parents=True)
    res = do_repo(repo, output_dir=tdir, last=None, summary=True)
    print(f"Rendered summary: {res}")
    print("Opening in browser....")
    check_call(['xdg-open', str(res)])


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

def setup_parser(p):
    p.add_argument('queries', type=str, nargs='+')


def run(args):
    # TODO FIXME
    with TemporaryDirectory() as td:
        tdir = Path(td)
        try:
            do_run(queries=args.queries, sources=['github'], tdir=tdir)
            # TODO open html??
        except Exception as e:
            logger.exception(e)
            raise e
        finally:
            print("Press any key when ready")
            getch()





