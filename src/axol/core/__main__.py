import importlib

import click

from .storage import Database


@click.group()
def main() -> None:
    pass


@main.command(name='search')
@click.argument('module', required=True)
@click.argument('query', required=True)
@click.option('--quiet/-q', is_flag=True)
def cmd_search(*, module: str, query: str, quiet: bool) -> None:
    """
    Search only, won't modify the databases.

    Example:

        search axol.modules.hackernews.search whatever
    """
    # TODO deserialize?
    # and raw mode that doesn't try to deserialise?
    search_module = importlib.import_module(module)
    for uid, j in search_module.search(query=query):
        if not quiet:
            print(uid, j)


@main.command(name='crawl')
def cmd_crawl() -> None:
    """
    Search all queries in the config and save in the databases.
    """
    import axol.user_config as C
    for config in C.configs():
        # TODO move this away to something abstracted away from configs module?
        for query in config.queries:
            query_res = config.search(query)
            # FIXME should query and dedup in bulk
            # otherwise fails at db insertion time
            with Database(config.db_path) as db:
                db.insert(query_res)


@main.command(name='feed')
def cmd_feed() -> None:
    # TODO add argument for name and list?
    import axol.user_config as C
    for config in C.configs():
        # FIXME read only mode or something?
        # definitely makes sense considering constructor creates the db if it doesn't exist
        with Database(config.db_path) as db:
            for uid, j in db.select_all():
                try:
                    pj = config.parse(j)
                except Exception as e:
                    print("WHILE PARSING", j)
                    raise e
                print(uid, pj)


# TODO special mode to run test method from search module??
# import subprocess
# import sys
# subprocess.check_call([sys.executable, '-m', 'pytest', '-s', __file__])


if __name__ == '__main__':
    main()


# FIXME for hn crawling same query may give different sets of results at a very short timespan?
# try querying the same thing every 5 mins to check
