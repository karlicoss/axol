#!/usr/bin/env python3
import json
from datetime import datetime
from collections import OrderedDict
from itertools import islice
from pathlib import Path
from typing import Optional

from .common import ichunks
from .storage import RepoHandle, DbHelper, Jsons

from kython.klogging2 import LazyLogger

log = LazyLogger('axol.database', level='info')


from sqlalchemy import func, select, text # type: ignore


class DbWriter:

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path


    def commit(self, *, sha: str, dt: datetime, jsons: Jsons, query: str) -> None:
        db = DbHelper(db_path=self.db_path)
        # TODO thinkj about sha/dt??
        # TODO that should probably be extracted? to support new results as well
        pre_total = len(jsons) if isinstance(jsons, list) else -1
        log.info('processing %s %s (%s results)', sha, dt, pre_total)

        # TODO not sure when I should handle ignored? maybe prune later?

        # iterative still makes sense, since insert_many splits
        dtstr = dt.isoformat()

        duplicates = 0

        # meh, but querying a database 10K times can't be fast enough I guess
        existing_blobs = {
            row[0] for row in db.connection.execute(select([db.results.c.blob]))
        }

        total = 0
        def iter_unique():
            nonlocal total
            for j in jsons:
                total += 1
                # ordereddict isn't super necessary on python 3.6+, but just in case..
                json_sorted = OrderedDict(sorted(j.items()))
                # TODO hmm. maybe use cachew mappings here?
                blob = json.dumps(json_sorted)

                uid = j['uid']
                db_dict = {
                    db.UID : uid,
                    db.DT  : dtstr,
                    db.BLOB: blob,
                }
                # dataset:
                # - with duplicate detection:
                #   ./database.py github_lifelogging  12.59s user 2.41s system 77% cpu 19.248 total
                # - no duplicate detection:
                #   ./database.py github_lifelogging  3.17s  user 2.27s system 38% cpu 14.020 total
                #   eh. it's not massively faster
                # sqlalchemy:
                # - with duplicate detection
                #   ./database.py github_lifelogging  9.87s  user 1.70s system 94% cpu 12.186 total
                # - no duplicate detection
                #   ./database.py github_lifelogging  2.67s  user 1.91s system 48% cpu 9.469 total


                # sqlalchemy:
                # - with duplicate detection
                #   oh wow, it takes _really_ long time; didn't even bother waiting to finish
                # - no duplicate detection, no updates
                #   ./database.py /L/coding/axol/outputs/twitter_lifelogging  6.01s user 0.85s system 67% cpu 10.145 total
                # - duplicate detection with a hashset, no updates
                #   ./database.py /L/coding/axol/outputs/twitter_lifelogging  7.39s user 0.91s system 102% cpu 8.128 total
                #   TODO might need to watch out for memory?..
                # - duplicates with a hashet, single query update
                #   ./database.py /L/coding/axol/outputs/twitter_lifelogging  6.61s user 0.82s system 92% cpu 8.049 total
                #   O

                # TODO maybe on conflict ignore?
                existing = blob in existing_blobs
                if not existing:
                    # eh, don't like this vvvv, but on the other hand that saves us from duplicates in the input data
                    existing_blobs.add(blob)
                    yield db_dict
                else:
                    nonlocal duplicates
                    duplicates += 1
        chunk_size = 1000
        for chunk in ichunks(iter_unique(), n=chunk_size):
            db.connection.execute(db.results.insert(), chunk)

        # compute updates; while it's possible to figure out later, nice to have it for logging
        # ugh. I'm too lazy to figure this out in sqlalchemy...
        groups = list(db.connection.execute(text('''
SELECT A.uid, COUNT(*) FROM
results AS A
JOIN
results AS B
ON  A.dt  = :dtstr
AND A.uid = B.uid
GROUP BY A.uid;
        '''), dtstr=dtstr))
        updates = 0
        for (_, gsize) in groups:
            if gsize > 1:
                updates += 1
        [(total,)] = db.connection.execute(func.count(db.results))

        logline = f'''
query     : {query}
results   : {total}
duplicates: {duplicates}
updates   : {updates}
total     : {total}
        '''.strip()

        log.info(' '.join(logline.splitlines()))
        db.connection.execute(db.logs.insert(), [{
            db.DT_COL : dtstr,
            db.LOG_COL: logline,
        }])
        # TODO size might be innacurate during the connection?

        log.info('database %s, size %.2f Mb', self.db_path, self.db_path.stat().st_size / 10 ** 6)
        db.close()


# TODO can remove this later
def convert_old(db: Path, *, repo: Path):
    assert db.suffix == '.sqlite' # just in case..
    query = repo # TODO use name/proper query??

    root = Path(__file__).absolute().parent.parent
    if repo.is_absolute():
        git_repo = repo
    else:
        git_repo = root / 'outputs' / repo
    assert git_repo.is_dir(), git_repo
    rh = RepoHandle(git_repo)

    db_path = db
    assert not db_path.exists(), db_path # this is only for first time conversion

    log.info('using database %s', db_path)

    for snapshot in rh.iter_versions():
        sha, dt, jsons = snapshot
        writer = DbWriter(db_path=db_path)
        writer.commit(sha=sha, dt=dt, jsons=jsons, query=query)
# TODO implement a test for idempotence?
