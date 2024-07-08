import re
import time
from typing import Any

from loguru import logger
import orjson
import requests

from axol.core.common import notnone, Json, SearchResults, Uid
from .query import SearchQuery, Kind


def _search(
    *,
    query: str,
    limit: int | None,
    do_request,
    kind: Kind,
) -> SearchResults:
    qstr = f'{kind=} {query=}'

    logger.info(f'{qstr} -- fetching...')

    start = 0
    uids: dict[Uid, bytes] = {}
    expected_total = -1  # this will be set on first fetch
    while True:
        if limit is not None and len(uids) >= limit:
            break

        resp = do_request(query=query, start=start)
        html = resp.text

        # 20 is used on pinboard website (in the 'earlier results' link)
        # NOTE seems that in the browser or curl, pinboard might return >20 items on the first page for tag search
        # however, somehow via requests it's still 20?
        # also I feel like the website has a bug, the 'earlier' link goes in 50 increments
        # however pages past the first one display 20 items only??
        start += 20

        ## just a sanity check
        html_count = html.count('class="bookmark_title')
        js_count = html.count('bmarks[')
        assert html_count == js_count, (html_count, js_count)
        ##

        m = re.search(r'Found(?: about)?\s+(\S+)\s+results', html)
        if m is not None:
            expected_total = int(m.group(1).replace(',', ''))
        else:
            m = re.search(r'"bookmark_count">(\d*?)<.span>', html)
            if m is None:
                assert 'No results found' in html  # regular search returned 0 results
                expected_total = 0
                break
            else:
                ts = m.group(1)
                if len(ts) == 0:
                    expected_total = 0
                    break
                expected_total = int(ts)

        logger.debug(f'{qstr} -- expected total {expected_total}')

        js_data = notnone(re.search('var bmarks={};(.*?)</script>', html, re.DOTALL)).group(1)
        split = re.split(r'bmarks.\d+. = ', js_data)
        assert split[0].strip() == '', split[0]  # first is newline or empty
        split = split[1:]

        if len(split) == 0:
            logger.debug(f'{qstr} -- no more results')
            break

        for s in split:
            s = s.rstrip(';')
            if len(s) == 0:
                # sometimes seems to happen?
                continue
            j: Json = orjson.loads(s)

            # so for uid it also has j['id']
            # but it's not exposed anywhere outside, in bookmark permalink we see the slug
            # the permalink seems to always have user id too
            # however if I replace user with an arbitrary string, it works
            # https://pinboard.in/u:_/b:a95fd8864c28
            # so just bookmark slug must be unique enough
            uid = j['slug']
            assert isinstance(uid, str), j  # just in case

            if uid in uids:
                # race conditions might happen due to the pagination
                continue

            # eh. not sure what is it, sometimes can be 500 as well?
            # assert j.get('code', None) in {'200', None}, j  # just in case

            bs = s.encode('utf8')
            uids[uid] = bs
            yield uid, bs
        logger.debug(f'{qstr} -- fetched {len(uids)} results so far')
        time.sleep(5)  # to avoid spam

    total = len(uids)
    logger.info(f'{qstr} -- got {total} results')

    assert expected_total >= 0

    if limit is None and expected_total > 10:
        assert total / expected_total > 0.9, (total, expected_total)  # just in case, maybe make defensive later


def _do_request_regular(*, query: str, start: int) -> requests.Response:
    params = {
        'query': query,
        'all': 'Search All',
        'start': str(start),
    }
    return requests.get(
        url='https://pinboard.in/search',
        params=params,
    )


def _do_request_tag(*, query: str, start: int) -> requests.Response:
    params = {
        'start': str(start),
    }
    return requests.get(
        url=f'https://pinboard.in/t:{query}',
        params=params,
    )


_REQUESTERS: dict[Kind, Any] = {
    'regular': _do_request_regular,
    'tag': _do_request_tag,
}


def search(query: SearchQuery, *, limit: int | None) -> SearchResults:
    requester = _REQUESTERS[query.kind]
    yield from _search(query=query.query, limit=limit, do_request=requester, kind=query.kind)
