from abc import abstractmethod
from dataclasses import dataclass
from functools import partial
from typing import Any, Callable, Iterator, Protocol, Sequence, cast

import github
from github import (
    Github,
    GithubException,  # TODO handle exceptions later?
)
from github.Commit import Commit
from github.ContentFile import ContentFile
from github.Issue import Issue
from github.Repository import Repository
from github.GithubObject import NotSet, Opt

from loguru import logger

from axol.core.common import SearchResults, Uid
from .query import GithubQuery, Kind


REQUIRES = ['PyGithub']


def _get_sorts(sorts: Sequence[str]) -> Sequence[tuple[Opt[str], Opt[str]]]:
    # github trims api results to 1000 (last checked 20240626)
    # so we can get a bit more by varying sort and order
    res: list[tuple[Opt[str], Opt[str]]] = [(NotSet, NotSet)]  # best match
    for sort in sorts:
        for order in ['asc', 'desc']:
            res.append((sort, order))
    return res


class Mixin(Protocol):
    sorts: tuple[str, ...]
    method: Callable  # meh
    KIND: Kind


@dataclass
class Search(Mixin):  # todo make it typed?
    api: Github

    @abstractmethod
    def get_uid(self, x: Any) -> Uid:
        raise NotImplementedError

    def search(self, *, query: str, limit: int | None) -> SearchResults:
        sorts = _get_sorts(self.sorts)
        method = self.__class__.method  # hmm otherwise python binds it??
        searcher = partial(method, self.api)

        qstr = f'kind={self.KIND} {query=} {sorts=}'
        logger.info(f'{qstr} -- fetching...')

        def _search(*, sort: Opt[str], order: Opt[str]) -> Iterator[tuple[Uid, Any]]:
            uids: dict[Uid, Any] = {}
            for i, x in enumerate(searcher(query=query, sort=sort, order=order)):
                if limit is not None and i >= limit:
                    return

                uid = self.get_uid(x)

                is_dupe = uid in uids # check uniqueness just in case
                if is_dupe:
                    if isinstance(x, Commit):  # meh, maybe make it a specific class attribute?
                        # commits can be duplicated due to forks
                        # just skip
                        continue
                    else:
                        assert uid not in uids, (uid, uids[uid])

                uids[uid] = x
                yield uid, x


        uids: dict[Uid, ContentFile] = {}
        # todo maybe, only use additional when there is close to 100 results??
        for sort, order in sorts:
            logger.debug(f'kind={self.KIND} {query=} {sort=!r:<10} {order=!r:<5} searching...')
            # TODO make this merging generic
            # kinda tricky since we don't want to convert dupes to json prematurely..
            added = 0
            for uid, x in _search(sort=sort, order=order):
                if uid in uids:
                    continue
                uids[uid] = x
                added += 1

                # ugh, so there is x.raw_data, however it incurs an api call
                # same with x.content and some other getters

                j = x._rawData
                # TODO this contains a lot of spam, especially in 'repository' key
                # migtt be worth pruning

                yield uid, j
            logger.debug(f'{query=} {sort=!r:<10} {order=!r:<5} {added=}')

        total = len(uids)
        logger.info(f'{qstr} -- got {total} results')


@dataclass
class SearchCode(Search):
    KIND: Kind = 'code'
    method = Github.search_code
    # ugh. for code search orders and sort are deprecated
    # see
    # - https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28#search-code
    # - https://github.blog/changelog/2023-03-10-changes-to-the-code-search-api/
    # - https://github.com/orgs/community/discussions/52932
    sorts: tuple[str, ...] = ()

    def get_uid(self, x: ContentFile) -> Uid:
        # todo could also take html_url and chop off the sha?
        return x.repository.full_name + ':' + x.path


@dataclass
class SearchRepositories(Search):
    KIND: Kind = 'repositories'
    method = Github.search_repositories

    sorts: tuple[str, ...] = ('stars', 'forks', 'updated')

    def get_uid(self, x: Repository) -> Uid:
        return x.full_name


@dataclass
class SearchIssues(Search):
    KIND: Kind = 'issues'
    method = Github.search_issues

    # see https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28#search-issues-and-pull-requests
    sorts: tuple[str, ...] = ('comments', 'created', 'updated')
    # FIXME these aren't working in github library due to a hard assert
    # 'reactions',
    # 'interactions',

    def get_uid(self, x: Issue) -> Uid:
        # FIXME not sure about this
        return str(x.id)


@dataclass
class SearchCommits(Search):
    KIND: Kind = 'commits'
    method = Github.search_commits

    sorts: tuple[str, ...] = ('author-date', 'committer-date')

    def get_uid(self, x: Commit) -> Uid:
        return x.sha


def search(*, query: GithubQuery | str, limit: int | None) -> SearchResults:
    if isinstance(query, str):
        query = GithubQuery(query=query)

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

    for Searcher in [
        SearchRepositories,
        SearchIssues,
        SearchCommits,
        SearchCode,
    ]:
        if not query.include(Searcher.KIND):
            continue
        searcher = Searcher(api=api)  # type: ignore[abstract]
        yield from searcher.search(query=query.query, limit=limit)
