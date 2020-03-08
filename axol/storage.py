import gc
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from itertools import groupby
from subprocess import DEVNULL, check_output, run
from typing import Dict, Generic, Iterator, List, Tuple, Type, TypeVar, Any

from axol.common import logger, slugify
from axol.jsonify import JsonTrait
from axol.traits import get_result_type, ignore_result


import sqlalchemy
from sqlalchemy import Table, Column, func


class DbHelper:
    UID  = 'uid'
    DT   = 'dt'
    BLOB = 'blob'

    DT_COL  = 'dt'
    LOG_COL = 'log'

    def __init__(self, db_path: Path) -> None:
        self.engine = sqlalchemy.create_engine(f'sqlite:///{db_path}')
        self.connection = self.engine.connect()
        meta = sqlalchemy.MetaData(self.connection)

        # TODO read only mode?
        self.results = Table(
            'results',
            meta,
            Column(self.UID , sqlalchemy.String),
            Column(self.DT  , sqlalchemy.String),
            Column(self.BLOB, sqlalchemy.String),
            # NOTE: using unique index for blob doesn't give any benefit?
            # TODO later, might worth it for DT, UID? or primary key?
        )
        self.results.create(self.connection, checkfirst=True)

        self.logs = Table(
            'logs',
            meta,
            Column(self.DT_COL , sqlalchemy.String),
            Column(self.LOG_COL, sqlalchemy.String),
        )
        self.logs.create(self.connection, checkfirst=True)


    def close(self):
        # TODO engine?
        self.connection.close()
   


Revision = str
Json = Dict

class RepoHandle:
    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.logger = logger

    def _check_output(self, *args):
        cmd = [
            'git', f'--git-dir={self.repo}/.git', *args
        ]
        last = None
        for _ in range(10):
            try:
                return check_output(cmd)
            except OSError as e:
                raise e
                last = e
                if 'Cannot allocate memory' in str(e):
                    self.logger.debug(' '.join(cmd))
                    self.logger.error('cannot allocate memory... trying GC and again')
                    gc.collect()
                    time.sleep(2)
                else:
                    raise e
        else:
            assert last is not None
            raise last


    def _get_revisions(self) -> List[Tuple[str, datetime]]:
        """
        returns in order of ascending timestamp
        """
        ss = list(reversed(self._check_output(
            'log',
            '--pretty=format:%h %ad',
            '--no-patch',
        ).decode('utf8').splitlines()))
        def pdate(l):
            ds = ' '.join(l.split()[1:])
            return datetime.strptime(ds, '%a %b %d %H:%M:%S %Y %z')
        return [(l.split()[0], pdate(l)) for l in ss]

    def _get_content(self, rev: str) -> str:
        return self._check_output(
            'show',
            rev + ':content.json',
        ).decode('utf8')

    def iter_versions(self, last=None) -> Iterator[Tuple[Revision, datetime, Json]]:
        revs = self._get_revisions()
        if last is not None:
            revs = revs[-last: ]
        for rev, dd in revs:
            self.logger.debug('processing %s %s', rev, dd)
            cc = self._get_content(rev)
            if len(cc.strip()) == 0:
                j: Json = {}
            else:
                j = json.loads(cc)
            yield (rev, dd, j)

# TODO shit, Json means Jsons really...
class DbRepoHandle:
    # TODO rename repo to db?
    def __init__(self, repo: Path) -> None:
        if '/outputs/' in str(repo): # TODO temporary hack for migration period..
            repo = Path(str(repo).replace('/outputs/', '/databases/') + '.sqlite')
        self.repo = repo; assert self.repo.is_file()
        self.logger = logger

    def iter_versions(self, last=None) -> Iterator[Tuple[Revision, datetime, Json]]:
        assert last is None # not sure if I need it??
        # TODO make up revisions??
        # TODO how to open in read only mode?
        dbh = DbHelper(db_path=self.repo)

        results = dbh.results

        cursor = dbh.connection.execute(results.select().order_by(results.c.dt))
        for dts, group in groupby(cursor, key=lambda row: row[1]): # TODO meh, hardcoded..
            revision = dts # meh
            dt = datetime.fromisoformat(dts)
            jsons = [json.loads(g[2]) for g in group]
            yield revision, dt, jsons


# TODO I guess need to compare here?
class Collector:
    def __init__(self):
        self.items: Dict[str, Any] = {}

    def register(self, batch):
        added = []
        for i in batch:
            if i.uid in self.items:
                pass # TODO FIXME compare? if description or tags changed, report it?
            else:
                added.append(i)
                self.items[i.uid] = i
        return added

R = TypeVar('R')

# TODO uh. kinda pointless class... could just be a dict?
class Changes(Generic[R]):
    def __init__(self) -> None:
        self.changes: Dict[datetime, List[R]] = {}
    # method to format everything?

    def add(self, rev: datetime, items) -> None:
        assert rev not in self.changes # TODO not sure
        self.changes[rev] = items

    def __len__(self):
        return sum(len(x) for x in self.changes.values())

# TODO html mode??
def get_digest(repo: Path, last=None) -> Changes[R]:
    rtype = get_result_type(repo)
    Trait = JsonTrait.for_(rtype)
    from_json = Trait.from_json

    rh = RepoHandle(repo)
    # rh = DbRepoHandle(repo)
    # ustats = get_user_stats(jsons, rtype=rtype)
    ustats = None

    # TODO shit. should have stored metadata in repository?... for now guess from filename..

    cc = Collector()
    changes: Changes[R] = Changes()
    # TODO maybe collector can figure it out by itself? basically track when the item was 'first se
    # TODO would be interesting to have non-consuming slice...
    for jj in rh.iter_versions(last=last):
        rev, dd, j = jj
        items = []

        for x in j:
            item = from_json(x)
            ignored = ignore_result(item)
            if ignored is not None:
                logger.debug('ignoring due to %s', ignored)
                continue
            # TODO would be nice to propagate and render... also not collect such items in the first place??
            items.append(item)


        added = cc.register(items)
        #print(f'revision {rev}: total {len(cc.items)}')
        #print(f'added {len(added)}')
        # if first:
        if len(added) == 0:
            continue

        # TODO what is 'formatted'?? I guess it was for stable git changes
        formatted = list(sorted(added, key=lambda e: e.when, reverse=True))
        # not sure if should keep revision here at all..
        #
        changes.add(dd, formatted)
        # TODO link to user
        # TODO user weight?? count is fine I suppose...
        # TODO added date
#        if len(added) > 0:
#            for r in sorted(added, key=lambda r: r.uid):
#                # TODO link to bookmark
#                # TODO actually chould even generate html here...
#                # TODO highlight interesting users
#                # TODO how to track which ones were already notified??
#                # TODO I guess keep latest revision in a state??

    return changes


def slugify_in(path: str, dir: Path):
    dd = os.listdir(str(dir))
    while True:
        res = slugify(path)
        if res not in dd:
            return res
        path = path + '_'


# TODO reuse RepoHandle? not sure..
class RepoWriteHandle:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.logger = logger

    @classmethod
    def create(cls, name: str, base: Path):
        dname = slugify(name) # TODO FIXME slugify_in?
        rpath = base.joinpath(dname)
        rpath.mkdir(exist_ok=True)
        return RepoWriteHandle(rpath)

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
