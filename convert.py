#!/usr/bin/env python3
from pathlib import Path

def map_repo(git: Path) -> Path:
    assert git.parent.name == 'outputs'
    dbdir = git.parent.parent / 'databases'
    for x in {'hackernews_', 'reddit_', 'twitter_', 'github_'}:
        if git.name.startswith(x):
            dbname = git.name
            break
    else:
        # must be pinboard
        dbname = 'pinboard_' + git.name
    return dbdir / (dbname + '.sqlite')


def doit(git: Path, db: Path):
    import subprocess
    subprocess.check_call([
        './database.py',
        git,
        '--to', db
    ])


def main():
    repos = list(sorted(Path('outputs').absolute().iterdir()))
    dbs = list(map(map_repo, repos))


    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor() as pool:
        pool.map(doit, repos, dbs)


if __name__ == '__main__':
    main()
