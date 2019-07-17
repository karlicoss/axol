import gc
import json
import time
from datetime import datetime
from pathlib import Path
from subprocess import check_output
from typing import Dict, Generic, Iterator, List, Tuple, Type, TypeVar

from axol.common import logger
from axol.jsonify import JsonTrait
from axol.traits import get_result_type, ignore_result


Revision = str
Json = Dict

class RepoHandle:
    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.logger = logger

    def check_output(self, *args):
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


    def get_revisions(self) -> List[Tuple[str, datetime]]:
        """
        returns in order of ascending timestamp
        """
        ss = list(reversed(self.check_output(
            'log',
            '--pretty=format:%h %ad',
            '--no-patch',
        ).decode('utf8').splitlines()))
        def pdate(l):
            ds = ' '.join(l.split()[1:])
            return datetime.strptime(ds, '%a %b %d %H:%M:%S %Y %z')
        return [(l.split()[0], pdate(l)) for l in ss]

    def get_content(self, rev: str) -> str:
        return self.check_output(
            'show',
            rev + ':content.json',
        ).decode('utf8')

    def iter_versions(self, last=None) -> Iterator[Tuple[Revision, datetime, Json]]:
        revs = self.get_revisions()
        if last is not None:
            revs = revs[-last: ]
        for rev, dd in revs:
            self.logger.debug('processing %s %s', rev, dd)
            cc = self.get_content(rev)
            if len(cc.strip()) == 0:
                j: Json = {}
            else:
                j = json.loads(cc)
            yield (rev, dd, j)


def test_repo_handle():
    from config import OUTPUTS
    hh = RepoHandle(OUTPUTS / 'bret_victor')
    assert len(list(hh.iter_versions())) > 5


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
        self.changes[rev] = items

    def __len__(self):
        return sum(len(x) for x in self.changes.values())

# TODO html mode??
def get_digest(repo: Path, last=None) -> Changes[R]:
    rtype = get_result_type(repo)
    Trait = JsonTrait.for_(rtype)
    from_json = Trait.from_json

    rh = RepoHandle(repo)
    # ustats = get_user_stats(jsons, rtype=rtype)
    ustats = None

    # TODO shit. should have stored metadata in repository?... for now guess from filename..

    cc = Collector()
    changes = Changes[R]() # TODO ?? does it really add getitem??
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
        formatted = list(sorted(added, key=lambda e: e.when, reverse=True))
        # not sure if should keep revision here at all..
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


def test_digest():
    from config import OUTPUTS
    dd = get_digest(OUTPUTS / 'bret_victor')
    from itertools import chain
    everything = list(chain.from_iterable(v for _, v in dd.changes.items()))
    assert len(everything) == len({x.uid for x in everything})
