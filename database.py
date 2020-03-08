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
    # TODO results??
    results = db.get_table('results')
    # TODO 'log' table??

    # TODO ugh. can't use multiple columns...
    # primary_id=UID, primary_type=db.types.text)

    # TODO ugh. use sqlalchemy? would be nice to verify the schema...


    for snapshot in rh.iter_versions():
        sha, dt, jsons = snapshot
        log.info('processing %s %s (%d results)', sha, dt, len(jsons))

        # TODO not sure when I should handle ignored? maybe prune later?

        # TODO what is 'formatted'?? I guess it was for stable git changes
        #
        # TODO update db

        # iterative still makes sense, since insert_many splits

        duplicates = 0
        def iter_unique():
            for j in jsons:
                # ordereddict isn't super necessary on python 3.6+, but just in case..
                json_sorted = OrderedDict(sorted(j.items()))
                blob = json.dumps(json_sorted)

                dtstr = dt.isoformat()
                db_dict = {
                    UID : j['uid'],
                    'dt': dtstr,
                    BLOB: blob,
                }
                found = list(results.find(**{BLOB: blob}))
                if len(found) == 0:
                    yield db_dict
                else:
                    nonlocal duplicates
                    duplicates += 1

        # ok, insert_many is quite a bit faster
        results.insert_many(iter_unique())

        # TODO log to db?
        log.info('filtered out %d/%d duplicates', duplicates, len(jsons))



def main():
    with TemporaryDirectory() as tdir:
        td = Path(tdir)
        run(td)


if __name__ == '__main__':
    main()
