from pathlib import Path
from subprocess import check_call
from tempfile import TemporaryDirectory
from typing import Sequence

from kython.tui import getch

from .common import Query, slugify, logger
from .crawl import process_query
from .report import do_repo
from .queries import GithubQ, RedditQ


def do_run_one(queries: Sequence[str], source: str, tdir: Path):
    searchers = [Cls(source,  *queries) for Cls in [GithubQ, RedditQ]]
    [q] = [s for s in searchers if s.sname == source]

    dry = False
    process_query(q, path=tdir, dry=dry)

    repo = tdir / q.repo_name
    for d in ('summary', 'rendered'):
        (tdir / d).mkdir(exist_ok=True, parents=True)
    res = do_repo(repo, output_dir=tdir, last=None, summary=True)
    print(f"Rendered summary: {res}")
    print("Opening in browser....")
    check_call(['xdg-open', str(res)])


def do_run(queries: Sequence[str], sources: Sequence[str], tdir: Path):
    for src in sources:
        # TODO run in parallel?
        do_run_one(queries=queries, source=src, tdir=tdir)


def setup_parser(p):
    p.add_argument('queries', type=str, nargs='+')


def run(args):
    with TemporaryDirectory() as td:
        tdir = Path(td)
        try:
            do_run(queries=args.queries, sources=['github', 'reddit'], tdir=tdir)
        except Exception as e:
            logger.exception(e)
            raise e
        finally:
            print("Press any key when ready")
            getch()





