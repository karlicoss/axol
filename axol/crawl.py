#!/usr/bin/env python3
import argparse
from pathlib import Path
import logging
import sys

from .common import logger, Query, slugify
from .jsonify import to_json
from .database import DbWriter

from config import get_queries, DATABASES


def process_query(q: Query, dry: bool, path: Path) -> None:
    logger.info('crawler: processing %s', q)
    searcher = q.searcher()
    qs = q.queries

    if dry:
        logger.info(f'dry run! would have searched for {qs} via {searcher}')
        return

    results = searcher.search_all(qs)
    jsons = [to_json(r) for r in results]


    dbstem = slugify(q.repo_name) # TODO FIXME slugify_in?
    db_path = path / (dbstem + '.sqlite')
    dbw = DbWriter(db_path=db_path)
    dbw.commit(jsons, query=str(qs))


def process_all(dry=False, include=None, exclude=None, name=None) -> None:
    ok = True
    def reg_error(err):
        nonlocal ok
        logger.error('error while retreiving stuff')
        if isinstance(err, Exception):
            logger.exception(err)
        else:
            logger.error(err)
        ok = False

    one = False
    for q in get_queries(include=include, exclude=exclude, name=name):
        one = True
        try:
            process_query(q, dry=dry, path=DATABASES)
        except Exception as e:
            reg_error(e)
    if not one:
        reg_error(RuntimeError('No queries matched!'))

    if not ok:
        logger.error("Had errors during processing!")
        sys.exit(1)

def run(args):
    process_all(args.dry, include=args.include, exclude=args.exclude, name=args.name)


def setup_parser(p) -> None:
    p.add_argument('--dry', action='store_true')
    p.add_argument('--include', action='append')
    p.add_argument('--exclude', action='append')
    p.add_argument('--name', type=str, required=False, help='name as specified in config.py')
    # TODO ugh.
    # p.add_argument('repos', nargs='*')


def main() -> None:
    p = argparse.ArgumentParser()
    setup_parser(p)
    args = p.parse_args()
    run(args)


if __name__ == '__main__':
    main()

