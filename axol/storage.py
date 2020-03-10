import gc
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from subprocess import DEVNULL, check_output, run
from typing import Dict, Generic, Iterator, List, Tuple, Type, TypeVar, Any, Iterable

from .common import logger, slugify
from .jsonify import JsonTrait
from .traits import get_result_type, ignore_result
from .database import Revision, Json, Jsons, DbReader


# TODO FIXME should rely on a DB here
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

    rh = DbReader(repo)
    # TODO need to update pinboard?
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
