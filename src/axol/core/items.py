from pathlib import Path
from .storage import Database


if __name__ == '__main__':
    # TODO ok.. so how to pick the correct model from just database?
    # probs will need to specify it explicitly?
    # import axol.modules.hackernews.model as M
    # db_path = Path('test.sqlite')

    import axol.modules.reddit.model as M
    db_path = Path('reddit.sqlite')

    # FIXME read only or something?
    # definitely makes sense considering constructor creates the db if it doesn't exist
    with Database(db_path) as db:
        for uid, j in db.select_all():
            try:
                pj = M.parse(j)
            except Exception as e:
                print("WHILE PARSING", j)
                raise e
            print(uid, pj)

# TODO rename to feed?
