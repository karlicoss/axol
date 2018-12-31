#!/usr/bin/env python3

import os
from pathlib import Path
import json
import re
import logging
import sys
from subprocess import check_call, run, DEVNULL
from typing import Union

from kython.logging import setup_logzero

from config import pinboard

def get_logger():
    return logging.getLogger('info-crawler')


logger = get_logger()
setup_logzero(logger, level=logging.INFO)

def slugify(s: str):
    s = s.strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)

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

RP = Path('outputs')


class RepoHandle:
    def __init__(self, path: Path) -> None:
        self.path = path

    def assert_clean(self):
        if self._git('rev-parse', 'HEAD', stderr=DEVNULL).returncode == 0:
            self._git('diff', '--exit-code').check_returncode()
        else:
            logger.info('%s: empty repo!', self.path)

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

ok = True

for p in pinboard:
    # TODO make sure names are unique??
    # dname = slugify_in(p.name, dir=RP)
    dname = slugify(p.name)
    rpath = RP.joinpath(dname)
    rpath.mkdir(exist_ok=True)
    rh = RepoHandle(rpath)
    try:
        import spinboard
        setup_logzero(spinboard.get_logger(), level=logging.DEBUG)
        logger.info('spinboard: getting %s', p.queries)
        results = spinboard.Spinboard().search_all(p.queries)
        jsons = [r.json for r in results]
        rh.commit(jsons)
    except Exception as e:
        logger.error('error while retreiving spinboard')
        logger.exception(e)
        ok = False




if not ok:
    sys.exit(1)
