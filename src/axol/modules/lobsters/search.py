import itertools
import re
import time
from typing import assert_never

from bs4 import BeautifulSoup
from loguru import logger
import requests

from axol.core.common import SearchResults, Uid, make_uid
from .common import extract_uid
from .query import SearchQuery, Kind


def _search_order(query: str, *, kind: Kind, order: str, limit: int | None) -> SearchResults:
    qstr = f'{query=} {kind=} {order=}'
    logger.info(f'{qstr} -- fetching...')

    # looks like on lobsters quotes in query would result in 0 results
    assert "'" not in query, query

    uids: dict[Uid, bytes] = {}
    expected_total = -1  # will be set on first search
    for page in itertools.count(start=1):
        if limit is not None and len(uids) >= limit:
            break

        r = requests.get(
            'https://lobste.rs/search',
            params={
                'q': query,
                'order': order,
                'page': str(page),
                'what': kind,
            },
        )

        soup = BeautifulSoup(r.text, "html.parser")
        if expected_total == -1:
            [total_e] = soup.select('.searchresults .heading')
            m = re.fullmatch(r'(\d+) results for', total_e.text.strip())
            assert m is not None
            expected_total = int(m.group(1))
            logger.debug(f'{qstr} -- expected total {expected_total}')

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

            item = str(item_el).encode('utf8')
            if b'Story removed by submitter' in item:
                # doesn't have link/title, not much we can do?
                logger.debug(f'{qstr}: skipping {uid}, story removed by submitter')
                # TODO subtract from expected total??
                continue

            uids[uid] = item
            yield uid, item

        if len(item_els) == 0:
            logger.debug(f'{qstr} -- no more results')
            break
        logger.debug(f'{qstr} -- fetched {len(uids)} results so far')
        time.sleep(1)

    total = len(uids)
    logger.info(f'{qstr} -- got {total} results')
    if limit is None and expected_total > 10:
        assert total / expected_total > 0.7, (total, expected_total)  # just in case, maybe make defensive later


def _search(query: str, *, kind: Kind, limit: int | None) -> SearchResults:
    qstr = f'{query=} {kind=}'
    logger.info(f'{qstr} -- fetching...')
    uids: dict[Uid, bytes] = {}
    for order in ['relevance', 'score', 'newest']:
        for uid, item in _search_order(query=query, kind=kind, order=order, limit=limit):
            if uid in uids:
                continue
            uids[uid] = item
            yield uid, item
    logger.info(f'{qstr} -- fetched {len(uids)} results total')


def search(query: SearchQuery, *, limit: int | None) -> SearchResults:
    yield from _search(query=query.query, kind=query.kind, limit=limit)
