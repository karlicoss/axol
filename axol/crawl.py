#!/usr/bin/env python3
import argparse
from pathlib import Path
import logging
import sys

from kython.klogging import setup_logzero

from axol.common import logger, Query
from axol.jsonify import to_json
from axol.storage import RepoWriteHandle

from config import get_queries, OUTPUTS


def process_query(q, dry: bool, path=None):
    logger.info('crawler: processing %s', q)
    searcher = q.searcher()
    qs = q.queries

    if dry:
        logger.info(f'dry run! would have searched for {qs} via {searcher}')
        return

    results = searcher.search_all(qs)
    jsons = [to_json(r) for r in results]

    rh = RepoWriteHandle.create(q.repo_name, base=path)
    rh.commit(jsons)


def process_all(dry=False, include=None, exclude=None):
    ok = True
    def reg_error(err):
        nonlocal ok
        logger.error('error while retreiving stuff')
        if isinstance(err, Exception):
            logger.exception(err)
        else:
            logger.error(err)
        ok = False

    for q in get_queries(include=include, exclude=exclude):
        try:
            process_query(q, dry=dry)
        except Exception as e:
            reg_error(e)

    if not ok:
        logger.error("Had errors during processing!")
        sys.exit(1)

def run(args):
    process_all(args.dry, include=args.include, exclude=args.exclude)


def setup_parser(p):
    p.add_argument('--dry', action='store_true')
    p.add_argument('--include', action='append')
    p.add_argument('--exclude', action='append')


def main():
    setup_logzero(logging.getLogger('spinboard'), level=logging.DEBUG)

    p = argparse.ArgumentParser()
    setup_parser(p)
    args = p.parse_args()
    run(args)


if __name__ == '__main__':
    main()

