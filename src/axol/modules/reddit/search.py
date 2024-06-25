from typing import Any, Iterator

from loguru import logger
import praw  # type: ignore[import-untyped]
from praw.models import PollData, PollOption, Redditor, Submission, Subreddit  # type: ignore[import-untyped]

from axol.core.common import  SearchResults, Uid


REQUIRES = ['praw']


def debug_praw() -> None:
    import logging
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger = logging.getLogger('prawcore')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
# debug_praw()


def _ignore_item(key: str, value: Any) -> bool:
    if callable(value):
        return True

    if key.startswith('_'):
        return True

    return False


# sadly praw doesn't keep raw json data :( https://github.com/praw-dev/praw/issues/830
def jsonify(d):
    if isinstance(d, (str, float, int, bool, type(None))):
        return d

    if isinstance(d, list):
        return [jsonify(x) for x in d]

    if isinstance(d, dict):
        return {k: jsonify(v) for k, v in d.items() if not _ignore_item(k, v)}

    if isinstance(d, (
        PollData,
        PollOption,
        Redditor,
        Submission,
        Subreddit,
    )):
        return jsonify(vars(d))

    raise RuntimeError(f"Unexpected type: {type(d)}")


def _uid(r: Submission) -> Uid:
    u = r.id
    assert isinstance(u, Uid)  # just in case
    return u


def search(*, query: str, limit: int | None) -> SearchResults:
    # note limit is purely to somewhat limit number of api calls
    # e.g. here it would likely return more results
    logger.info(f'query:{query} -- fetching...')

    # FIXME support domain queries?
    assert 'domain:' not in query
    from axol.user_config import reddit_praw  # type: ignore[attr-defined]
    api = praw.Reddit(
        user_agent='axol',
        **reddit_praw.credentials(),
    )
    searcher = api.subreddit('all')

    def _search(sort_by: str) -> Iterator[Submission]:
        uids: dict[Uid, Submission] = {}
        for r in searcher.search(query=query, limit=limit, sort=sort_by):
            # NOTE: reddit api only allows to search in submissions, no comments :(
            assert isinstance(r, Submission), r

            uid = _uid(r)
            # check uniqueness just in case
            assert uid not in uids, (r, uids[uid])
            uids[uid] = r
            yield r

    # results are slightly different for different sort orders
    # e.g. you can try searching 'promnesia',
    # relevance returns 48 results, hot -- 28 results, rest 39 results
    # what is more, when there are hundreds of results, overlap can be basically 0
    # so we merge the results to get as much as we can
    sort_bys = ['relevance', 'hot', 'top', 'new', 'comments']

    # TODO different queries might result in same results as well
    # TODO merge should be shared, merge via uid?
    # might be easier to ignore on database level? not sure
    uids: dict[Uid, Submission] = {}
    for sort_by in sort_bys:
        for r in _search(sort_by=sort_by):
            uid = _uid(r)
            if uid in uids:
                continue
            uids[uid] = r
            # FIXME not sure if need to sort here?
            yield uid, jsonify(r)
    total = len(uids)
    logger.info(f'query:{query} -- got {total} results')

# TODO yield query as well?
# might be useful to have it in the db

# TODO maybe search should be named after specific search provier? like praw
# or reddit.search.praw/via_praw

# NOTE: seems like for reddit, multiple terms are treated like some sort of fuzzy search?
# not exactly OR either
