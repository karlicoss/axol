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
    # TODO results??
    results = db.get_table('results')
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

        for_db = []
        for j in jsons:
            # ordereddict isn't super necessary on python 3.6+, but just in case..
            json_sorted = OrderedDict(sorted(j.items()))
            jsonstr = json.dumps(json_sorted)

            dtstr = dt.isoformat()
            for_db.append({
                UID   : j['uid'],
                'dt'  : dtstr,
                'blob': jsonstr,
            })

        # ok, for_db is quite a bit faster
        results.insert_many(for_db)


def main():
    with TemporaryDirectory() as tdir:
        td = Path(tdir)
        run(td)


if __name__ == '__main__':
    main()
