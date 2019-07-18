#!/usr/bin/env python3
import argparse

import os
from pathlib import Path
import json
import re
import logging
import time
import sys
from subprocess import check_call, run, DEVNULL
from typing import Union

from kython.klogging import setup_logzero

from axol.common import logger, Query

from config import slugify, get_queries, OUTPUTS
from axol.jsonify import to_json

Pathish = Union[str, Path]

# TODO should I slugify_in??
# TODO I guess that should be on initialization??
def slugify_in(path: str, dir: Pathish):
    dd = os.listdir(str(dir))
    while True:
        res = slugify(path)
        if res not in dd:
            return res
        path = path + '_'

# TODO reuse repo handle from storage??
class RepoHandle:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.logger = logger

    @classmethod
    def create(cls, name: str, path=OUTPUTS):
        dname = slugify(name)
        rpath = path.joinpath(dname)
        rpath.mkdir(exist_ok=True)
        return RepoHandle(rpath)

    def assert_clean(self):
        if self._git('rev-parse', 'HEAD', stderr=DEVNULL).returncode == 0:
            self._git('diff', '--exit-code').check_returncode()
        else:
            self.logger.info('%s: empty repo!', self.path)

    def _git(self, *cmd, **kwargs):
        return run([
            'git',
            *cmd,
        ], cwd=str(self.path), **kwargs)

    def commit(self, jj):
        self._git('init', '--quiet').check_returncode()
        self.assert_clean()

        cpath = self.path.joinpath('content.json')
        before = None
        if cpath.exists():
            with cpath.open('r') as fo:
                jb = json.load(fo)
                before = len(jb)

        with cpath.open('w') as fo:
            json.dump(jj, fo, ensure_ascii=False, indent=1, sort_keys=True)
        self._git('add', 'content.json')
        self._git('commit', '-m', f'updated content ({before} -> {len(jj)} entries)', '--allow-empty').check_returncode()
        self.assert_clean()

# TODO make sure names are unique??
# TODO create dir there as well??

def process_query(q, dry: bool, path=None):
    logger.info('crawler: processing %s', q)
    searcher = q.searcher()
    qs = q.queries

    if dry:
        logger.info(f'dry run! would have searched for {qs} via {searcher}')
        return

    results = searcher.search_all(qs)
    jsons = [to_json(r) for r in results]

    rh = RepoHandle.create(q.repo_name, path=path)
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


def main():
    setup_logzero(logging.getLogger('spinboard'), level=logging.DEBUG)

    p = argparse.ArgumentParser()
    p.add_argument('--dry', action='store_true')
    p.add_argument('--include', action='append')
    p.add_argument('--exclude', action='append')
    args = p.parse_args()
    process_all(args.dry, include=args.include, exclude=args.exclude)


if __name__ == '__main__':
    main()

