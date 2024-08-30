# NOTE: for hn crawling same query may give different sets of results at a very short timespan
# try querying the same thing every 5 mins to check
import hn  # type: ignore[import-untyped]
import orjson

from axol.core.common import Json, SearchResults, _check, make_uid

# todo don't remember what type of imports I decided is best? absolute imports in modules??
from axol.core.logger import logger as global_logger

from .query import SearchQuery

REQUIRES = ['python-hn']


def fix_date_format() -> None:
    ## ugh. hasn't been updated for a while
    ## TODO maybe use algolia api directly?
    from hn.utils import AVAILABLE_DATE_FORMATS  # type: ignore[import-untyped]

    _date_format = '%Y-%m-%dT%H:%M:%SZ'
    if _date_format not in AVAILABLE_DATE_FORMATS:
        AVAILABLE_DATE_FORMATS.append(_date_format)


fix_date_format()


# todo would be nice to use some existing query language?
def _search(query: str, *, limit: int | None) -> SearchResults:
    assert isinstance(query, str), query  # should be mypy checked, but just in case

    logger = global_logger.bind(query=query)

    logger.info(f'{query=} -- fetching...')
    # https://www.algolia.com/doc/api-reference/api-parameters/advancedSyntax/#how-to-use
    # ok, so single quotes definitely don't work the same way double quotes are
    assert "'" not in query, query

    total = 0
    # search_by_date (from Algolia) means sorted by date, most recent first
    r: Json
    for r in hn.search_by_date(query):
        if limit is not None and total >= limit:
            break

        ## some stuff that algolia adds -- not useful to keep at all
        r.pop('_highlightResult', None)
        r.pop('_tags', None)
        ##

        uid = _check(r['objectID'], str)  # just in case

        total += 1
        yield make_uid(uid), orjson.dumps(r)

    logger.info(f'{query=} -- got {total} results')


def search(query: SearchQuery, *, limit: int | None) -> SearchResults:
    yield from _search(query=query.query, limit=limit)


def test() -> None:
    def check(query: str) -> int:
        slist = list(search(query=SearchQuery(query), limit=None))
        return len(slist)

    # NOTE: seems like it returns fuzzy results
    # e.g. one result here matches "bruderha"
    # ugh. this seems flaky???
    # assert check('bruderscha') == 2

    # space separated seem to work like an AND?
    assert check('grammar beepb00p') == 0

    assert check('"simplest job definition"') == 1

    # ugh. even web returns different results depending on whether search was incremental or not??
    # yeah, I think things are just changing depending on some caches which might get triggered by our test themselves..
    # sometimes retuns 34, sometimes 36
    assert check('simplest job definition') > 30

    # TODO hmm getting different number of results..
    # assert 500 < check('unexpected sequence') < 1000
