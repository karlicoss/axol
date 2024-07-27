from abc import abstractmethod
from dataclasses import dataclass
from functools import partial
from typing import Any, Callable, Iterator, Protocol, Sequence

from github import (
    Auth,
    Github,
    # GithubException,  # TODO handle exceptions later?
)
from github.Commit import Commit
from github.ContentFile import ContentFile
from github.Issue import Issue
from github.Repository import Repository
from github.GithubObject import NotSet, Opt

import orjson
from loguru import logger

from axol.core.common import SearchResults, Uid, Json, make_uid
from axol.credentials import github_token

from .query import Kind, SearchQuery


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

                is_dupe = uid in uids  # check uniqueness just in case
                if is_dupe:
                    if isinstance(x, Commit):  # meh, maybe make it a specific class attribute?
                        # commits can be duplicated due to forks
                        continue
                    elif isinstance(x, ContentFile):
                        # casn be duplicated due to identical matched blobs
                        continue
                    else:
                        assert uid not in uids, (uid, x, uids[uid])

                uids[uid] = x
                yield uid, x

        done_sort: set[Opt[str]] = set()
        uids: dict[Uid, ContentFile] = {}
        # todo maybe, only use additional when there is close to 100 results??
        for sort, order in sorts:
            qstr2 = f'kind={self.KIND} {query=} {sort=!r:<10} {order=!r:<5}'
            logger.debug(f'{qstr2} searching...')
            # TODO make this merging generic
            # kinda tricky since we don't want to convert dupes to json prematurely..
            found = 0
            added = 0
            for uid, x in _search(sort=sort, order=order):
                found += 1

                if found > 50 and added == 0:
                    # seems like we're not hitting any new results in this batch
                    if sort in done_sort:
                        # if we processed that sort before, likely means that previous order exhausted all new items
                        logger.debug(f'{qstr2}: bailing early, looks like already found all items')
                        break

                if uid in uids:
                    continue
                uids[uid] = x
                added += 1

                # ugh, so there is x.raw_data, however it incurs an api call
                # same with x.content and some other getters

                j: Json = x._rawData
                # TODO this contains a lot of spam, especially in 'repository' key
                # migtt be worth pruning

                yield uid, orjson.dumps(j)
            logger.debug(f'{query=} {sort=!r:<10} {order=!r:<5} {added=}')
            done_sort.add(sort)

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
        # hmm, so sha here seems to be literal hash of the matched blob?
        # it's not commit sha -- e.g. these repos are completely unrelated
        # - https://github.com/search?q=repo%3Atigthor%2Fneural-network-hacking%20promnesia&type=code
        # - https://github.com/search?q=repo%3AKayzaks%2FHackingNeuralNetworks%20promnesia&type=code
        # , they have the same sha
        return make_uid('code_' + x.sha)


@dataclass
class SearchRepositories(Search):
    KIND: Kind = 'repositories'
    method = Github.search_repositories

    sorts: tuple[str, ...] = ('stars', 'forks', 'updated')

    def get_uid(self, x: Repository) -> Uid:
        name = x.full_name.replace('/', '_')
        return make_uid('repo_' + name)


@dataclass
class SearchIssues(Search):
    KIND: Kind = 'issues'
    method = Github.search_issues

    # see https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28#search-issues-and-pull-requests
    sorts: tuple[str, ...] = ('comments', 'created', 'updated')
    # TODO these aren't working in github library due to a hard assert
    # 'reactions',
    # 'interactions',

    def get_uid(self, x: Issue) -> Uid:
        return make_uid('issue_' + str(x.id))


@dataclass
class SearchCommits(Search):
    KIND: Kind = 'commits'
    method = Github.search_commits

    sorts: tuple[str, ...] = ('author-date', 'committer-date')

    def get_uid(self, x: Commit) -> Uid:
        return make_uid('commit_' + x.sha)


SEARCHERS = {
    s.KIND: s
    for s in [
        SearchRepositories,
        SearchIssues,
        SearchCommits,
        SearchCode,
    ]
}


def search(query: SearchQuery, *, limit: int | None) -> SearchResults:
    # NOTE: hmm a bit too spammy, would be nice to disable response bodies?
    # github.enable_console_debug_logging()

    api = Github(
        auth=Auth.Token(github_token()),
        # couldn't find what's the max allowed search per_page
        # if we pass value bigger than 100 it works
        # but seems to still return only 100 results per batch
        per_page=100,
    )

    Searcher = SEARCHERS[query.kind]
    searcher = Searcher(api=api)  # type: ignore[abstract]
    yield from searcher.search(query=query.query, limit=limit)
