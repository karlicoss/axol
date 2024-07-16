from dataclasses import dataclass
from datetime import datetime

import orjson

from axol.core.common import datetime_aware, _check


@dataclass
class User:
    # we can't always reconstruct url from login due to bots or possibly some other edge cases
    login: str
    url: str


@dataclass
class Base:
    created_at: datetime_aware | None
    html_url: str
    user: User | None  # can be None if author deleted themselves?
    repo: str


@dataclass
class Code(Base):
    path: str


@dataclass
class Commit(Base):
    message: str


@dataclass
class Issue(Base):
    title: str
    body: str | None
    # todo total reactions count?


@dataclass
class Repository(Base):
    description: str | None
    topics: tuple[str]
    stars: int


Result = Code | Commit | Issue | Repository


def parse(data: bytes) -> Result:
    j = orjson.loads(data)

    entity_types = []
    # todo hmm might be easier to add entity type during search?
    if 'path' in j:
        entity_types.append('code')
    if 'commit' in j:
        entity_types.append('commit')
    if 'state' in j:
        entity_types.append('issue')
    if 'forks_count' in j:
        entity_types.append('repository')
    assert len(entity_types) == 1, (entity_types, j)
    [entity_type] = entity_types

    # todo later -- issues don't have it, only repository url?
    # j['repository'] = {
    #     # filter out weird 'templates'
    #     # TODO maybe delete them during scraping
    #     k: v
    #     for k, v in j['repository'].items()
    #     if not isinstance(v, str) or not ('api.github.com' in v and '{' in v and '}' in v)
    # }

    html_url = _check(j.pop('html_url'), str)

    if entity_type == 'code':
        repo = _check(j['repository']['full_name'], str)
        repo_owner = j['repository']['owner']
        path = _check(j.pop('path'), str)
        return Code(
            # FIXME doesn't contain commit date...
            # what would be a good datetime for it??
            # I think in old axol used repository pushed_at attribute??
            created_at=None,
            html_url=html_url,
            user=User(
                login=_check(repo_owner.pop('login'), str),
                url=_check(repo_owner.pop('html_url'), str),
            ),
            repo=repo,
            path=path,
        )
    elif entity_type == 'commit':
        repo = _check(j['repository']['full_name'], str)
        cmt = j.pop('commit')
        cmt_author = cmt.pop('author')
        created_at = datetime.fromisoformat(cmt_author['date'])
        message = _check(cmt.pop('message'), str)
        author = j.pop('author')
        user: User | None
        if author is None:
            # sometimes legit missing
            # e.g. https://github.com/indieweb/wiki/commit/5fa29b457ecb9015ecc02eaf4a3cd26bf1b4b44b
            # I guess means user deleted themselves?
            user = None
        else:
            user = User(
                login=_check(author.pop('login'), str),
                url=_check(author.pop('html_url'), str),
            )
        return Commit(
            created_at=created_at,
            html_url=html_url,
            user=user,
            repo=repo,
            message=message,
        )
    elif entity_type == 'issue':
        _prefix = 'https://api.github.com/repos/'
        repo_url = j['repository_url']
        repo = repo_url.removeprefix(_prefix)
        assert len(repo) < len(repo_url), (repo, repo_url)  # make sure chopped off

        title = _check(j.pop('title'), str)
        body = j.pop('body')
        created_at = datetime.fromisoformat(j.pop('created_at'))
        uu = j.pop('user')
        if uu is None:
            user = None
        else:
            user = User(
                login=_check(uu.pop('login'), str),
                url=_check(uu.pop('html_url'), str),
            )
        return Issue(
            created_at=created_at,
            html_url=html_url,
            user=user,
            repo=repo,
            title=title,
            body=body,
        )
    elif entity_type == 'repository':
        repo = _check(j['full_name'], str)
        created_at = datetime.fromisoformat(j.pop('created_at'))
        description = j.pop('description')  # can be none if empty
        topics = tuple(sorted(j.pop('topics')))
        stars = _check(j.pop('stargazers_count'), int)
        owner = j['owner']
        user = User(
            login=_check(owner.pop('login'), str),
            url=_check(owner.pop('html_url'), str),
        )
        return Repository(
            created_at=created_at,
            html_url=html_url,
            user=user,
            repo=repo,
            description=description,
            topics=topics,
            stars=stars,
        )
    else:
        raise RuntimeError(entity_type)
