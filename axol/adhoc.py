from pathlib import Path
from subprocess import check_call
from pprint import pprint
from tempfile import TemporaryDirectory
from typing import Sequence, List

from kython.tui import getch

from .common import Query, slugify, logger
from .crawl import process_query, setup_parser as setup_crawl_parser
from .report import do_repo
from .queries import GithubQ, RedditQ, TwitterQ, filter_queries, Query


SUPPORTED = [
    GithubQ,
    RedditQ,
    TwitterQ,
]

def do_run_one(query: Query, tdir: Path):
    dry = False
    process_query(query, path=tdir, dry=dry)

    repo = tdir / query.repo_name
    for d in ('summary', 'rendered'):
        (tdir / d).mkdir(exist_ok=True, parents=True)
    res = do_repo(repo, output_dir=tdir, last=None, summary=True)
    print(f"Rendered summary: {res}")
    print("Opening in browser....")
    check_call(['xdg-open', str(res)])


def do_run(queries: Sequence[Query], tdir: Path):
    for query in queries:
        # TODO run in parallel? e.g. split by source
        do_run_one(query=query, tdir=tdir)


def setup_parser(p):
    setup_crawl_parser(p)
    p.add_argument('queries', type=str, nargs='+')


def run(args):
    with TemporaryDirectory() as td:
        tdir = Path(td)
        qs = []
        for Cls in SUPPORTED:
            c = Cls('adhoc', *args.queries)
            qs.append(c)
        qs = filter_queries(qs, include=args.include, exclude=args.exclude)
        for q in qs:
            print(q.sname, qs)
        try:
            do_run(queries=qs, tdir=tdir)
        except Exception as e:
            logger.exception(e)
            raise e
        finally:
            print("Press any key when ready")
            getch()





