from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .storage import Database


Query = str  # TODO


@dataclass
class Config:
    queries: Sequence[Query]
    db_path: Path | str  # FIXME derive from crawler/repo 'name'?


if __name__ == '__main__':
    config = Config(
        queries=(
            # TODO duplicate query is a good test!
            'karlicoss',  # FIXME this query returns too many false positives for fuzzy match...
            'karlicoss',
            # 'beepb00p.xyz',
        ),
        db_path='test.sqlite',
    )

    # TODO move this inside config?
    import axol.modules.hackernews.search as S

    for query in config.queries:
        query_res = S.search(query)
        # FIXME should query and dedup in bulk
        # otherwise fails at db insertion time
        db_path = Path(config.db_path)
        # FIXME if relative, resolve relative to global storage dir?
        with Database(db_path) as db:
            db.insert(query_res)


# FIXME for hn crawling same query may give different sets of results at a very short timespan?
# try querying the same thing every 5 mins to check
