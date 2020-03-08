#!/usr/bin/env python3
import json
from collections import OrderedDict
from pathlib import Path
from tempfile import TemporaryDirectory

# from axol.common import setup_paths
from axol.storage import RepoHandle

from kython.klogging2 import LazyLogger

log = LazyLogger('axol')


def run(db_root: Path):
    query = 'arbtt' # TODO

    root = Path(__file__).absolute().parent
    git_repo = root / 'outputs/arbtt'; assert git_repo.is_dir()
    rh = RepoHandle(git_repo)

    # TODO assert repo doesnt exist
    db_path = db_root / 'arbtt.sqlite'

    log.info('using database %s', db_path)

    import dataset # type: ignore
    db = dataset.connect(f'sqlite:///{db_path}')

    UID = 'uid'
    BLOB = 'blob'

    results = db.get_table('results')
    # TODO ugh. can't use multiple columns...
    # primary_id=UID, primary_type=db.types.text)
    logs    = db.get_table('logs')


    # TODO ugh. use sqlalchemy? would be nice to verify the schema...

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
                    'dt': dtstr,
                    BLOB: blob,
                }
                existing = list(results.find(**{BLOB: blob}))
                if len(existing) == 0:
                    same_uid = list(results.find(**{UID: uid}))
                    if len(same_uid) > 0:
                        nonlocal updates
                        updates += 1

                    yield db_dict
                else:
                    nonlocal duplicates
                    duplicates += 1

        # ok, insert_many is quite a bit faster
        results.insert_many(iter_unique())

        logline = f'''
query     : {query}
results   : {len(jsons)}
duplicates: {duplicates}
updates   : {updates}
        '''.strip()

        log.info(' '.join(logline.splitlines()))
        logs.insert({
            'dt' : dtstr,
            'log': logline,
        })
    log.info('database %s, size %.2f Mb', db_path, db_path.stat().st_size / 10 ** 6)
    breakpoint()


def main():
    with TemporaryDirectory() as tdir:
        td = Path(tdir)
        run(td)


if __name__ == '__main__':
    main()
