import dataclasses
import importlib
import sys
from typing import Any

import click
from loguru import logger
from more_itertools import ilen

from .feed import get_feeds, Feed
from .query import compile_queries


@click.group()
def main() -> None:
    pass


arg_limit = click.option('--limit', type=int)
arg_include = click.option('--include', help='name filter for feeds to use')
arg_exclude = click.option('--exclude', help='name filter for feeds to use')
arg_quiet = click.option('--quiet/-q', is_flag=True, help='do not print anything')


@main.command(name='search')
@click.argument('module', required=True)
@click.argument('query', required=True)
@click.option('--raw', is_flag=True, help='print raw data, do not deserialize')
@arg_limit
@arg_quiet
def cmd_search(*, module: str, query: str, quiet: bool, limit: int | None, raw: bool) -> None:
    """
    Search only, won't modify the databases.

    Example:

        search axol.modules.hackernews.feed whatever
    """
    # FIXME maybe search should work against the config?.. and search_raw invoke the search module?
    feed_module = importlib.import_module(module)
    feed_class: type[Feed] = getattr(feed_module, 'Feed')
    feed = feed_class.make(query_name='adhoc', queries=[query])
    for uid, data in feed.search_all(limit=limit):
        if quiet:
            continue
        if raw:
            print(uid, data)
        else:
            print(uid, feed.parse(data))


@main.command(name='crawl')
@arg_limit
@arg_include
@arg_exclude
@arg_quiet
@click.option('--dry', is_flag=True, help='search and print results only, do not modify storage')
def cmd_crawl(*, limit: int | None, include: str | None, exclude: str | None, dry: bool, quiet: bool) -> None:
    """
    Search all queries in the feed and save in the databases.
    """
    feeds = get_feeds(include=include, exclude=exclude)
    errors = []
    total = 0
    for feed in feeds:
        for crawl_dt, uid, o in feed.crawl(limit=limit, dry=dry):
            if isinstance(o, Exception):
                logger.opt(exception=True).exception(o)
                errors.append(o)
                continue

            total += 1
            if quiet:
                continue
            print(uid, o)
    logger.info(f'crawled {total} new items')
    if len(errors) > 0:
        logger.error(f'got {len(errors)} errors')
        sys.exit(1)


@main.command(name='feed')
@arg_include
@arg_exclude
def cmd_feed(*, include: str | None, exclude: str | None) -> None:
    """
    Load feed from the database and print to stdout
    """
    feeds = get_feeds(include=include, exclude=exclude)
    errors = []
    for feed in feeds:
        for crawl_dt, uid, o in feed.feed():
            if isinstance(o, Exception):
                # TODO ugh. loguru is not tracing exc_info properly??
                # e.g. compare to
                # import logging; logging.exception(o, exc_info=o)
                logger.opt(exception=True).exception(o)
                errors.append(o)
            else:
                print(uid, o)
    if len(errors) > 0:
        logger.error(f'got {len(errors)} errors')
        sys.exit(1)


@main.command(name='prune')
@arg_include
@arg_exclude
@click.option('--dry', is_flag=True, help='only output items that would be pruned, do not actually prune')
def cmd_prune(*, include: str | None, exclude: str | None, dry: bool) -> None:
    """
    Prune items from the database according to the config

    This is useful if you excluded a bunch of items from the search and want to retroactively delete them from the db as well.
    """
    feeds = get_feeds(include=include, exclude=exclude)
    for feed in feeds:
        deleted = feed.prune_db(dry=dry)
        msg = f'[{feed}]: pruned {deleted} items {dry=}'
        if deleted > 0:
            logger.warning(msg)
        else:
            logger.info(msg)


@main.command(name='feeds')
@arg_include
@arg_exclude
@click.option('--search', is_flag=True, help='print raw search queries instead of config queries')
@click.option('--db-stats', is_flag=True, help='print database stats for the feed')
def cmd_feeds(*, include: str | None, exclude: str | None, search: bool, db_stats: bool) -> None:
    """
    Print out feeds defined in the config
    """
    feeds = get_feeds(include=include, exclude=exclude)

    datas = []
    for feed in feeds:
        tname = type(feed).__module__ + '.' + type(feed).__name__
        tname = tname.removeprefix('axol.modules')  # just for brevity when using default modules
        d: dict[str, Any] = {
            'Type': tname,
        }

        if search:
            squeries = compile_queries(feed.queries)
            for sq in squeries:
                d = {
                    **d,
                    **dataclasses.asdict(sq),
                }
                datas.append(d)
        else:
            queries = feed.queries
            if len(queries) == 1:
                queries = queries[0]  # just for brevity
            d = {
                **d,
                'name': feed.name,
                'queries': queries,
                'exclude': feed.exclude_raw is not None,  # eh, it's a function so can't pretty print
            }
            if db_stats:
                db_items = ilen(feed.feed()) if feed.db_path.exists() else -1
                d['db_items'] = db_items
            datas.append(d)

    import tabulate

    print(tabulate.tabulate(datas, headers='keys', stralign='right'))


# TODO special mode to run test method from search module??
# import subprocess
# import sys
# subprocess.check_call([sys.executable, '-m', 'pytest', '-s', __file__])


if __name__ == '__main__':
    main()

# TODO think about more consistent logging... would be nice to get a feed specific sublogger?
