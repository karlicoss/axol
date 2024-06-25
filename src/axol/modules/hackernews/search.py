from loguru import logger
import hn  # type: ignore[import-untyped]

# TODO don't remember what type of imports I decided is best?
# absolute imports in modules??
from axol.core.common import SearchResults, Uid


REQUIRES = ['python-hn']


def fix_date_format() -> None:
    ## ugh. hasn't been updated for a while
    ## TODO maybe use algolia api directly?
    from hn.utils import AVAILABLE_DATE_FORMATS  # type: ignore[import-untyped]
    _date_format = '%Y-%m-%dT%H:%M:%SZ'
    if _date_format not in AVAILABLE_DATE_FORMATS:
        AVAILABLE_DATE_FORMATS.append(_date_format)
fix_date_format()


# TODO would be nice to use some existing query language?
def search(*, query: str, limit: str | None) -> SearchResults:
    # todo doesn't really support limit? warn if not none?

    logger.info(f'query:{query} -- fetching...')
    # https://www.algolia.com/doc/api-reference/api-parameters/advancedSyntax/#how-to-use
    # ok, so single quotes definitely don't work the same way double quotes are
    assert "'" not in query, query

    # TODO looks like you can precede a word with - to exclude from query?
    # TODO maybe always search for exact match for simplicity?
    # and to disable typo tolerance

    total = 0
    # search_by_date (from Algolia) means sorted by date, most recent first
    for r in hn.search_by_date(query):
        ## some stuff that algolia adds -- not useful to keep at all
        r.pop('_highlightResult', None)
        r.pop('_tags', None)
        ##

        uid = r['objectID']
        assert isinstance(uid, Uid)  # just in case
        # FIXME think about post-filtering? dunno

        total += 1
        yield uid, r

    logger.info(f'query:{query} -- got {total} results')


def test() -> None:
    def check(query: str) -> int:
        slist = list(search(query=query, limit=None))
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
    assert check( 'simplest job definition' ) > 30

    # TODO hmm getting different number of results..
    # assert 500 < check('unexpected sequence') < 1000
