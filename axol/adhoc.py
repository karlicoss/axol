from pathlib import Path
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import Sequence

from kython.tui import getch

from .common import Query, slugify, logger
from .crawl import process_query
from .report import do_repo
from .queries import GithubQ



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


def setup_parser(p):
    p.add_argument('queries', type=str, nargs='+')


def run(args):
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





