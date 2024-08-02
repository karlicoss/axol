import itertools
import re
import time
from typing import assert_never

from bs4 import BeautifulSoup
import loguru
import requests

from axol.core.common import SearchResults, Uid, make_uid
from axol.core.logger import logger as main_logger
from .common import extract_uid
from .query import SearchQuery, Kind


def _search_order(
    query: str,
    *,
    kind: Kind,
    order: str,
    limit: int | None,
    total_so_far: int,
    logger: 'loguru.Logger',
) -> SearchResults:
    logger = logger.bind(order=order)

    logger.info('fetching...')

    # results in bizarre matches.. not sure why
    assert '/' not in query, query

    uids: set[Uid] = set()
    expected_total = -1  # will be set on first search
    for page in itertools.count(start=1):
        if limit is not None and len(uids) >= limit:
            break

        while True:
            r = requests.get(
                'https://lobste.rs/search',
                params={
                    'q': query,
                    'order': order,
                    'page': str(page),
                    'what': kind,
                },
            )
            if re.search('Throttled, sleep.* between hits', r.text):
                logger.debug('lobste.rs suggested to sleep between hits, waiting...')
                time.sleep(5)
            else:
                break

        soup = BeautifulSoup(r.text, "html.parser")
        if expected_total == -1:
            [total_e] = soup.select('.searchresults .heading')
            m = re.fullmatch(r'(\d+) results? for', total_e.text.strip())
            assert m is not None, total_e
            expected_total = int(m.group(1))
            logger.debug(f'expected total {expected_total}')

        if expected_total == total_so_far:
            # this is so we don't do unnecessary queries
            # lobsters only returns 20 pages of results (while displaying the correct overall total)
            # so this logic works for us
            logger.debug('looks like already fetched everything before, bailing early')
            return

        if kind == 'stories':
            [items_container] = soup.select('.stories.list')
            item_els = items_container.select('.story')
        elif kind == 'comments':
            [items_container] = soup.select('.comments')
            item_els = items_container.select('.comment')
        else:
            assert_never(kind)

        for item_el in item_els:
            uid = make_uid(extract_uid(item_el))

            if uid in uids:
                # can have race condition due to pagination
                # NOTE actually sometimes happens really consistently, usually after 4th or so page..
                # but after a few reruns stops happening?? could be some search engine caches or something like that
                # note sure why but whatever
                # TODO might need to adjust the total / expected_total ratio below if it keeps happening
                continue
            uids.add(uid)

            item = str(item_el).encode('utf8')
            if b'Story removed by submitter' in item:
                # doesn't have link/title, not much we can do?
                logger.debug(f'skipping {uid}, story removed by submitter')
                # TODO subtract from expected total??
                continue

            yield uid, item

        if len(item_els) == 0:
            logger.debug('no more results')
            break
        logger.debug(f'fetched {len(uids)} results so far')
        time.sleep(2)  # seems that it sometimes suggests to sleep(1), so doing 2 just in case

    total = len(uids)
    logger.info(f'got {total} results')
    if limit is None and expected_total > 10:
        assert total / expected_total > 0.7, (total, expected_total)  # just in case, maybe make defensive later


def _search(query: str, *, kind: Kind, limit: int | None) -> SearchResults:
    logger = main_logger.bind(query=query, kind=kind)

    logger.info('fetching...')
    uids: set[Uid] = set()
    for order in ['newest', 'relevance', 'score']:
        total_so_far = len(uids)
        for uid, item in _search_order(query=query, kind=kind, order=order, limit=limit, total_so_far=total_so_far, logger=logger):
            if uid in uids:
                continue
            uids.add(uid)
            yield uid, item
    logger.info(f'fetched {len(uids)} results total')


def search(query: SearchQuery, *, limit: int | None) -> SearchResults:
    yield from _search(query=query.query, kind=query.kind, limit=limit)
