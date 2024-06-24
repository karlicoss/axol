import re
import time

from loguru import logger
import orjson
import requests

from axol.core.common import notnone, Json, SearchResults, Uid


def search(query: str, limit: int | None) -> SearchResults:
    # FIXME support tag queries etc
    # or search them automatically?
    logger.info(f'query:{query} -- fetching...')

    search_url = 'https://pinboard.in/search'

    start = 0
    uids: dict[Uid, Json] = {}
    expected_total = -1  # this will be set on first fetch
    while True:
        if limit is not None and len(uids) >= limit:
            break

        params = {
            # TODO will it quote_plus automatically?? check
            # q = urllib.parse.quote_plus(query)  # TODO
            # works for Search All
            'query': query,
            'all': 'Search All',
            'start': str(start),
        }
        resp = requests.get(url=search_url, params=params)
        start += 20  # this is used on pinboard website (in the 'earlier results' link)

        html = resp.text

        expected_total = int(notnone(re.search(r'Found\s+(\d+)\s+results', html)).group(1))
        logger.debug(f'query:{query} -- expected total {expected_total}')

        js_data = notnone(re.search('var bmarks={};(.*?)</script>', html, re.DOTALL)).group(1)
        split = re.split(r'bmarks.\d+. = ', js_data)
        assert split[0].strip() == '', split[0]  # first is newline or empty
        split = split[1:]

        if len(split) == 0:
            logger.debug(f'query:{query} -- no more results')
            # TODO warn if a lot of mismatch with expected_total??
            break

        for s in split:
            s = s.rstrip(';')
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

            uids[uid] = j
            yield uid, j
        logger.debug(f'query:{query} -- fetched {len(uids)} results so far')
        time.sleep(5)  # to avoid spam

    total = len(uids)

    assert expected_total >= 0

    if limit is None and expected_total > 10:
        assert total / expected_total > 0.9, (total, expected_total)  # just in case, maybe make defensive later

