import dataclasses
import importlib
from typing import Any

import click
from loguru import logger
import orjson

from .config import get_configs, Config
from .query import compile_queries


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

        search axol.modules.hackernews.config whatever
    """
    # TODO deserialize?
    # and raw mode that doesn't try to deserialise?
    config_module = importlib.import_module(module)
    config_class: type[Config] = getattr(config_module, 'Config')
    config = config_class.make(query_name='adhoc', queries=[query])
    for uid, jblob in config.search_all(limit=limit):
        if not quiet:
            j = orjson.loads(jblob)
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
        results = config.search_all(limit=limit)

        if dry:
            for uid, jblob in results:
                j = orjson.loads(jblob)
                print(uid, config.parse(j))
        else:
            config.insert(results)


@main.command(name='feed')
@arg_include
def cmd_feed(*, include: str | None) -> None:
    # TODO add argument for name and list?
    configs = get_configs(include=include)
    for config in configs:
        for uid, crawl_dt, j in config.select_all():
            try:
                # TODO move parse inside select_all?
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
        tname = type(config).__module__ + '.' + type(config).__name__
        tname = tname.removeprefix('axol.modules')  # just for brevity when using default modules
        d: dict[str, Any] = {
            'Type': tname,
        }

        if search:
            squeries = compile_queries(config.queries)
            for sq in squeries:
                d = {
                    **d,
                    **dataclasses.asdict(sq),
                }
                datas.append(d)
        else:
            queries = config.queries
            if len(queries) == 1:
                queries = queries[0]  # just for brevity
            d = {
                **d,
                'name': config.name,
                'queries': queries,
                'exclude': config.exclude is not None,  # eh, it's a function so can't pretty print
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
