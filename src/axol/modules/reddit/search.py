REQUIRES = ['praw']

from typing import Any, Iterator

from loguru import logger
import praw
from praw.models import PollData, PollOption, Redditor, Submission, Subreddit


def debug_praw() -> None:
    import logging
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger = logging.getLogger('prawcore')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
# debug_praw()


Json = Any


def _ignore_item(key: str, value: Any) -> bool:
    if callable(value):
        return True

    if key.startswith('_'):
        return True

    return False


# sadly praw doesn't keep raw json data :( https://github.com/praw-dev/praw/issues/830
def jsonify(d) -> Json:
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


def _uid(r: Submission) -> str:
    u = r.id
    assert isinstance(u, str)  # just in case
    return u


def search(query: str) -> Iterator[Json]:
    # FIXME support domain queries?
    assert 'domain:' not in query
    # FIXME add limit support
    # TODO limit is purely to limit number of api calls
    from axol_config import reddit
    api = praw.Reddit(
        user_agent='axol',
        **reddit.praw_credentials(),
    )
    searcher = api.subreddit('all')

    def _search(sort_by: str) -> Iterator[Submission]:
        uids: dict[str, Submission] = {}
        for r in searcher.search(query=query, limit=None, sort=sort_by):
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
    uids: dict[str, Submission] = {}
    for sort_by in sort_bys:
        for r in _search(sort_by=sort_by):
            uid = _uid(r)
            if uid in uids:
                continue
            uids[uid] = r
            # FIXME not sure if need to sort here?
            yield jsonify(r)


# TODO move main stuff to common?
import click


@click.group()
def main() -> None:
    pass


@main.command(name='test')
def cmd_test() -> None:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, '-m', 'pytest', '-s', __file__])


@main.command(name='search')
@click.argument('query', required=True)
def cmd_search(query: str) -> None:
    total = 0
    for r in search(query): # f'"{query}"'):
        print(r)
        total += 1
    logger.info(f'[reddit] fetched {total} results')


if __name__ == '__main__':
    main()

# FIXME maybe search should be named after
