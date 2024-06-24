from pathlib import Path
from .storage import Database


if __name__ == '__main__':
    import axol.modules.hackernews.model as M
    # FIXME read only or something?
    # definitely makes sense considering constructor creates the db if it doesn't exist
    db_path = Path('test.sqlite')
    with Database(db_path) as db:
        for uid, j in db.select_all():
            try:
                pj = M.parse(j)
            except Exception as e:
                print("WHILE PARSING", j)
                raise e
            print(uid, pj)

# TODO rename to feed?
