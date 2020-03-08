#!/usr/bin/env python3
from pathlib import Path
from tempfile import TemporaryDirectory

# from axol.common import setup_paths
from axol.storage import RepoHandle


def run(db_root: Path):
    root = Path(__file__).absolute().parent
    git_repo = root / 'outputs/arbtt'; assert git_repo.is_dir()
    rh = RepoHandle(git_repo)

    # TODO assert repo doesnt exist

    for snapshot in rh.iter_versions():
        sha, dt, jsons = snapshot

        # TODO not sure when I should handle ignored? maybe prune later?

        # TODO what is 'formatted'?? I guess it was for stable git changes
        #

        # TODO update db
    pass


def main():
    with TemporaryDirectory() as tdir:
        td = Path(tdir)
        run(td)


if __name__ == '__main__':
    main()
