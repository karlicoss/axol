from dataclasses import dataclass
from datetime import datetime

from axol.core.common import datetime_aware, Json, _check


@dataclass
class Base:
    created_at: datetime_aware | None
    html_url: str


@dataclass
class Commit(Base):
    message: str
    author_login: str | None


@dataclass
class Code(Base):
    pass


@dataclass
class Issue(Base):
    title: str
    body: str
    # todo total reactions count?
    user_login: str | None


@dataclass
class Repository(Base):
    description: str | None
    topics: tuple[str]
    stars: int


Result = Code | Commit | Issue | Repository


def parse(j: Json) -> Result:
    j = {k: v for k, v in j.items()}
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
        return Code(
            # FIXME doesn't contain commit date...
            # what would be a good datetime for it??
            created_at=None,
            html_url=html_url,
        )
    elif entity_type == 'commit':
        cmt = j.pop('commit')
        cmt_author = cmt.pop('author')
        created_at = datetime.fromisoformat(cmt_author['date'])
        message = _check(cmt.pop('message'), str)
        author = j.pop('author')
        author_login: str | None
        if author is None:
            # sometimes legit missing
            # e.g. https://github.com/indieweb/wiki/commit/5fa29b457ecb9015ecc02eaf4a3cd26bf1b4b44b
            # I guess means user deleted themselves?
            author_login = None
        else:
            author_login = _check(author.pop('login'), str)
        return Commit(
            created_at=created_at,
            html_url=html_url,
            message=message,
            author_login=author_login,
        )
    elif entity_type == 'issue':
        title = _check(j.pop('title'), str)
        body = _check(j.pop('body'), str)
        created_at = datetime.fromisoformat(j.pop('created_at'))
        user_login: str | None
        user = j.pop('user')
        if user is None:
            user_login = None
        else:
            user_login = _check(user.pop('login'), str)
        return Issue(
            created_at=created_at,
            html_url=html_url,
            title=title,
            body=body,
            user_login=user_login,
        )
    elif entity_type == 'repository':
        created_at = datetime.fromisoformat(j.pop('created_at'))
        description = j.pop('description')  # can be none if empty
        topics = tuple(sorted(j.pop('topics')))
        stars = _check(j.pop('stargazers_count'), int)
        return Repository(
            created_at=created_at,
            html_url=html_url,
            description=description,
            topics=topics,
            stars=stars,
        )
    else:
        raise RuntimeError(entity_type)
