from typing import Iterator

import github
from github import (
    Github,
    GithubException,  # TODO handle exceptions later?
)
from github.ContentFile import ContentFile
from github.GithubObject import NotSet, Opt

from loguru import logger

from axol.core.common import SearchResults, Uid


REQUIRES = ['PyGithub']


def search(*, query: str, limit: int | None) -> SearchResults:
    logger.info(f'query:{query} -- fetching...')
    # FIXME sort, order (asc/desc), highlight
    # todo what are qualifiers??
    # FIXME search_commits
    # FIXME search_repositories
    # FIXME search_topics

    # TODO hmm a bit too spammy
    # would be nice to disable response bodies?
    # github.enable_console_debug_logging()

    from axol.user_config import github as gh  # type: ignore[attr-defined]

    api = Github(
        login_or_token=gh.token(),
        # couldn't find what's the max allowed search per_page
        # if we pass value bigger than 100 it works
        # but seems to still return only 100 results per batch
        per_page=100,
    )

    def _search(*, order: Opt[str]) -> Iterator[tuple[Uid, ContentFile]]:
        uids: dict[Uid, ContentFile] = {}
        for x in api.search_code(query=query, order=order):
            if limit is not None and len(uids) >= limit:
                return

            # todo could also take html_url and chop off the sha?
            uid = x.repository.full_name + ':' + x.path

            # check uniqueness just in case
            assert uid not in uids, (uid, uids[uid])
            uids[uid] = x
            yield uid, x


    # github trims api results to 1000 (last checked 20240626)
    # so we can get a bit more by varying sort and order
    search_orders: list[Opt[str]] = ['asc', 'desc']
    # ugh. for code search orders and sort are deprecated
    # see
    # - https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28#search-code
    # - https://github.blog/changelog/2023-03-10-changes-to-the-code-search-api/
    # - https://github.com/orgs/community/discussions/52932
    search_orders = [NotSet]

    uids: dict[Uid, ContentFile] = {}
    # TODO maybe, only use additional when there is close to 100 results??
    # FIXME stars and forks are probably gonna give same results for descending?
    for order in search_orders:
        # TODO make this merging generic
        for uid, x in _search(order=order):
            if uid in uids:
                continue
            uids[uid] = x

            # ugh, so there is x.raw_data
            # however it incurs an api call
            # same with x.content etc

            j = x._rawData
            # TODO this contains a lot of spam, especially in 'repository' key
            # migtt be worth pruning

            yield uid, j

    total = len(uids)
    logger.info(f'query:{query} -- got {total} results')
