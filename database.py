#!/usr/bin/env python3
import json
from collections import OrderedDict
from itertools import islice
from pathlib import Path
from tempfile import TemporaryDirectory

from axol.common import ichunks
from axol.storage import RepoHandle

from kython.klogging2 import LazyLogger

log = LazyLogger('axol')


def run(db_root: Path, *, repo: str):
    query = repo # TODO

    root = Path(__file__).absolute().parent
    git_repo = root / 'outputs' / repo; assert git_repo.is_dir()
    rh = RepoHandle(git_repo)

    # TODO assert repo doesnt exist
    db_path = db_root / (repo + '.sqlite')

    log.info('using database %s', db_path)


    import sqlalchemy
    from sqlalchemy import Table, Column

    engine = sqlalchemy.create_engine(f'sqlite:///{db_path}')
    connection = engine.connect()
    meta = sqlalchemy.MetaData(connection)

    UID  = 'uid'
    DT   = 'dt'
    BLOB = 'blob'

    results = Table(
        'results',
        meta,
        Column(UID , sqlalchemy.String),
        Column(DT  , sqlalchemy.String),
        Column(BLOB, sqlalchemy.String), # TODO blob type??
    )
    results.create(connection, checkfirst=True)
    # TODO FIXME close connection

    # TODO ugh. can't use multiple columns...
    # primary_id=UID, primary_type=db.types.text)
    # logs    = db.get_table('logs')

    for snapshot in rh.iter_versions():
        sha, dt, jsons = snapshot
        # TODO that should probably be extracted? to support live database as well
        # TODO log query as well?
        log.info('processing %s %s (%d results)', sha, dt, len(jsons))

        # TODO not sure when I should handle ignored? maybe prune later?

        # TODO what is 'formatted'?? I guess it was for stable git changes
        #
        # TODO update db

        # iterative still makes sense, since insert_many splits
        dtstr = dt.isoformat()

        duplicates = 0
        updates    = 0

        def iter_unique():
            for j in jsons:
                # ordereddict isn't super necessary on python 3.6+, but just in case..
                json_sorted = OrderedDict(sorted(j.items()))
                blob = json.dumps(json_sorted)

                uid = j['uid']
                db_dict = {
                    UID : uid,
                    DT  : dtstr,
                    BLOB: blob,
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

        # TODO total maybe?
        logline = f'''
query     : {query}
results   : {len(jsons)}
duplicates: {duplicates}
updates   : {updates}
        '''.strip()

        log.info(' '.join(logline.splitlines()))
        # logs.insert({
        #     'dt' : dtstr,
        #     'log': logline,
        # })
        log.info('database %s, size %.2f Mb', db_path, db_path.stat().st_size / 10 ** 6)

    # breakpoint()


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('repo')
    args = p.parse_args()
    repo = args.repo

    with TemporaryDirectory() as tdir:
        td = Path(tdir)
        # TODO FIXME log actual query that was used
        run(td, repo=repo)


if __name__ == '__main__':
    main()
