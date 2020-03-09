#!/usr/bin/env python3
from pathlib import Path
from tempfile import TemporaryDirectory

from axol.database import DbWriter, log
from axol.storage import RepoHandle


# TODO can remove this later
def convert_old(db: Path, *, repo: Path):
    assert db.suffix == '.sqlite' # just in case..
    query = repo.name # TODO use proper query??

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
        writer._commit(sha=sha, dt=dt, jsons=jsons, query=query)
# TODO implement a test for idempotence?


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('repo', type=Path)
    p.add_argument('--to', type=Path, default=None)
    args = p.parse_args()

    to = args.to
    repo = args.repo

    if to is None:
        with TemporaryDirectory() as tdir:
            convert_old(Path(tdir) / (repo.name + '.sqlite'), repo=repo)
    else:
        convert_old(to, repo=repo)
