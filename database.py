#!/usr/bin/env python3
import json
from collections import OrderedDict
from itertools import islice
from pathlib import Path
from tempfile import TemporaryDirectory

from axol.common import ichunks
from axol.storage import RepoHandle, DbHelper

from kython.klogging2 import LazyLogger

log = LazyLogger('axol')


from sqlalchemy import func


def run(db_root: Path, *, repo: str):
    query = repo # TODO

    root = Path(__file__).absolute().parent
    git_repo = root / 'outputs' / repo; assert git_repo.is_dir()
    rh = RepoHandle(git_repo)

    db_path = db_root / (repo + '.sqlite')
    assert not db_path.exists(), db_path # this is only for first time conversion

    log.info('using database %s', db_path)


    dbh = DbHelper(db_path=db_path)
    connection = dbh.connection
    logs = dbh.logs
    results = dbh.results


    for snapshot in rh.iter_versions():
        sha, dt, jsons = snapshot
        # TODO that should probably be extracted? to support new results as well
        log.info('processing %s %s (%d results)', sha, dt, len(jsons))

        # TODO not sure when I should handle ignored? maybe prune later?

        # iterative still makes sense, since insert_many splits
        dtstr = dt.isoformat()

        duplicates = 0
        updates    = 0

        def iter_unique():
            for j in jsons:
                # ordereddict isn't super necessary on python 3.6+, but just in case..
                json_sorted = OrderedDict(sorted(j.items()))
                # TODO hmm. maybe use cachew mappings here?
                blob = json.dumps(json_sorted)

                uid = j['uid']
                db_dict = {
                    dbh.UID : uid,
                    dbh.DT  : dtstr,
                    dbh.BLOB: blob,
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

                # TODO maybe on conflict ignore?
                existing = list(connection.execute(results.select().where(
                    results.c.blob == blob,
                )))
                if len(existing) == 0:
                    # ok, slowdown from doing updates computation is pretty minimal (less than 5%)
                    same_uid = list(connection.execute(results.select().where(
                        results.c.uid == uid,
                    )))
                    if len(same_uid) > 0:
                        nonlocal updates
                        updates += 1

                    yield db_dict
                else:
                    nonlocal duplicates
                    duplicates += 1


        chunk_size = 1000
        for chunk in ichunks(iter_unique(), n=chunk_size):
            connection.execute(results.insert(), chunk)


        [(total,)] = connection.execute(func.count(results))

        logline = f'''
query     : {query}
results   : {len(jsons)}
duplicates: {duplicates}
updates   : {updates}
total     : {total}
        '''.strip()

        log.info(' '.join(logline.splitlines()))
        connection.execute(logs.insert(), [{
            dbh.DT_COL : dtstr,
            dbh.LOG_COL: logline,
        }])
        # TODO size might be innacurate during the connection?

        log.info('database %s, size %.2f Mb', db_path, db_path.stat().st_size / 10 ** 6)

    dbh.close()


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('repo')
    p.add_argument('--to', type=Path, default=None)
    args = p.parse_args()
    repo = args.repo

    # TODO FIXME log actual query that was used
    to = args.to
    if to is None:
        with TemporaryDirectory() as tdir:
            run(Path(tdir), repo=repo)
    else:
        assert to.is_dir()
        run(to, repo=repo)


# TODO implement a test for idempotence?


if __name__ == '__main__':
    main()
