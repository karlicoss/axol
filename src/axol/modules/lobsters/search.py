import itertools
import re
import time
from typing import assert_never

from bs4 import BeautifulSoup
from loguru import logger
import requests

from axol.core.common import SearchResults, Uid
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
            # FIXME not sure if they are overlapping between comments and stories?
            # maybe append kind?
            uid: str = item_el.attrs['data-shortid']
            assert len(uid) > 0, item_el  # just in case

            if uid in uids:
                # can have race condition due to pagination
                continue

            item = str(item_el).encode('utf8')
            if b'Story removed by submitter' in item:
                # doesn't have link/title
                continue

            uids[uid] = item
            # FIXME ugh. item type doesn't have to be json?? just bytes here?
            yield uid, item

        if len(item_els) == 0:
            logger.debug(f'{qstr} -- no more results')
            break
        logger.debug(f'{qstr} -- fetched {len(uids)} results so far')
        time.sleep(1)
    # FIXME log total stats?
    #
    total = len(uids)
    logger.info(f'{qstr} -- got {total} results')
    if limit is None and expected_total > 10:
        assert total / expected_total > 0.9, (total, expected_total)  # just in case, maybe make defensive later


def _search(query: str, *, kind: Kind, limit: int | None) -> SearchResults:
    qstr = f'{query=} {kind=}'
    logger.info(f'{qstr} -- fetching...')
    # FIXME merge by uid
    for order in ['relevance', 'score', 'newest']:
        yield from _search_order(query=query, kind=kind, order=order, limit=limit)
    # FIXME log total?


def search(query: SearchQuery, *, limit: int | None) -> SearchResults:
    yield from _search(query=query.query, kind=query.kind, limit=limit)
