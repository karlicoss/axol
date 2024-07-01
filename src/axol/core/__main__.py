import dataclasses
import importlib
from typing import Any

import click
from loguru import logger

from .config import get_configs
from .query import compile_queries
from .search import search_all
from .storage import Database


@click.group()
def main() -> None:
    pass


arg_limit = click.option('--limit', type=int)
arg_include = click.option('--include', help='name filter for search configs to use')


@main.command(name='search')
@click.argument('module', required=True)
@click.argument('query', required=True)
@click.option('--quiet/-q', is_flag=True)
@arg_limit
def cmd_search(*, module: str, query: str, quiet: bool, limit: int | None) -> None:
    """
    Search only, won't modify the databases.

    Example:

        search axol.modules.hackernews.search whatever
    """
    # TODO deserialize?
    # and raw mode that doesn't try to deserialise?
    search_module = importlib.import_module(module)
    for uid, j in search_module.search(queries=[query], limit=limit):
        if not quiet:
            print(uid, j)


@main.command(name='crawl')
@arg_limit
@arg_include
@click.option('--dry', is_flag=True, help='search and print results only, do not modify storage')
def cmd_crawl(*, limit: int | None, include: str | None, dry: bool) -> None:
    """
    Search all queries in the config and save in the databases.
    """
    configs = get_configs(include=include)
    for config in configs:
        results = search_all(search_function=config.search, queries=config.queries, limit=limit)

        if dry:
            for uid, j in results:
                print(uid, config.parse(j))
        else:
            with Database(config.db_path) as db:
                db.insert(results)


@main.command(name='feed')
@arg_include
def cmd_feed(*, include: str | None) -> None:
    # TODO add argument for name and list?
    configs = get_configs(include=include)
    for config in configs:
        # FIXME read only mode or something?
        # definitely makes sense considering constructor creates the db if it doesn't exist
        with Database(config.db_path) as db:
            for uid, crawl_dt, j in db.select_all():
                try:
                    pj = config.parse(j)
                except Exception as e:
                    logger.exception(e)
                    logger.error(f'while parsing {j}')
                    raise e
                print(uid, pj)


@main.command(name='configs')
@arg_include
@click.option('--search', is_flag=True)  # TODO think about something better
def cmd_configs(*, include: str | None, search: bool) -> None:
    configs = get_configs(include=include)

    datas = []
    for config in configs:
        d: dict[str, Any] = {
            'Type': type(config).__name__,
        }

        if search:
            squeries = compile_queries(config.queries)
            for sq in squeries:
                datas.append({
                    **d,
                    **dataclasses.asdict(sq),
                })
        else:
            assert dataclasses.asdict(config).keys() == {'name', 'queries'}, config
            queries = config.queries
            if len(queries) == 1:
                queries = queries[0]  # just for brevity
            d = {
                **d,
                'name': config.name,
                'queries': queries,
            }
            datas.append(d)

    import tabulate
    print(tabulate.tabulate(datas, headers='keys', stralign='right'))


# TODO special mode to run test method from search module??
# import subprocess
# import sys
# subprocess.check_call([sys.executable, '-m', 'pytest', '-s', __file__])


if __name__ == '__main__':
    main()


# FIXME for hn crawling same query may give different sets of results at a very short timespan?
# try querying the same thing every 5 mins to check
