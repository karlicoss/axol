#!/usr/bin/env python3
import json
from datetime import datetime
from collections import OrderedDict
from itertools import islice, groupby
from pathlib import Path
from typing import Optional, Iterator, Tuple, Dict, Iterable

from .common import ichunks, Query

import pytz
import sqlalchemy
from sqlalchemy import Table, Column
from sqlalchemy import func, select, text


Revision = str
Json = Dict
Jsons = Iterable[Json]


from .core.klogging import LazyLogger
logger = LazyLogger('axol.database', level='info')


class DbHelper:
    UID  = 'uid'
    DT   = 'dt'
    BLOB = 'blob'

    DT_COL  = 'dt'
    LOG_COL = 'log'

    def __init__(self, db_path: Path) -> None:
        self.engine = sqlalchemy.create_engine(f'sqlite:///{db_path}')
        self.connection = self.engine.connect()
        meta = sqlalchemy.MetaData()

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

        self.logs = Table(
            'logs',
            meta,
            Column(self.DT_COL , sqlalchemy.String),
            Column(self.LOG_COL, sqlalchemy.String),
        )

        meta.create_all(self.engine, checkfirst=True)

    def close(self):
        self.connection.close()
        self.engine.dispose()


class DbReader:
    # TODO rename repo to db?
    def __init__(self, repo: Path) -> None:
        # TODO remove this..
        if '/outputs/' in str(repo): # TODO temporary hack for migration period..
            repo = Path(str(repo).replace('/outputs/', '/databases/') + '.sqlite')
        self.repo = repo; assert self.repo.is_file(), self.repo


    def iter_versions(self, last=None) -> Iterator[Tuple[Revision, datetime, Jsons]]:
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

        dbh.close()


class DbWriter:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path


    def commit(self, jsons: Jsons, query: str) -> None:
        dt = datetime.now(tz=pytz.utc)
        return self._commit(
            sha='<DEPRECATED>', # TODO
            dt=dt,
            jsons=jsons,
            query=query,
        )


    # TODO could return stats?
    def _commit(self, *, sha: str, dt: datetime, jsons: Jsons, query: str) -> None:
        db = DbHelper(db_path=self.db_path)
        pre_batchsize = len(jsons) if isinstance(jsons, list) else -1
        logger.info('processing %s %s (%s results)', sha, dt, pre_batchsize)

        # TODO not sure when I should handle ignored? maybe prune later?

        # iterative still makes sense, since insert_many splits
        dtstr = dt.isoformat()

        duplicates = 0

        # meh, but querying a database 10K times can't be fast enough I guess
        existing_blobs = {
            row[0] for row in db.connection.execute(select(db.results.c.blob))
        }

        batchsize = 0
        def iter_unique():
            nonlocal batchsize
            for j in jsons:
                batchsize += 1
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
        '''), [dict(dtstr=dtstr)]))
        updates = 0
        for (_, gsize) in groups:
            if gsize > 1:
                updates += 1
        [(total,)] = db.connection.execute(select(func.count()).select_from(db.results))

        logline = f'''
query     : {query}
batchsize : {batchsize}
duplicates: {duplicates}
updates   : {updates}
total     : {total}
        '''.strip()

        logger.info(' '.join(logline.splitlines()))
        db.connection.execute(db.logs.insert(), [{
            db.DT_COL : dtstr,
            db.LOG_COL: logline,
        }])
        # TODO size might be innacurate during the connection?

        logger.info('database %s, size %.2f Mb', self.db_path, self.db_path.stat().st_size / 10 ** 6)
        db.connection.commit()
        db.close()
