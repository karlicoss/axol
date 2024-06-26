from dataclasses import dataclass
from datetime import datetime

from axol.core.common import datetime_aware, Json, _check


@dataclass
class Base:
    created_at: datetime_aware | None


@dataclass
class Commit(Base):
    html_url: str
    message: str
    author_login: str | None


@dataclass
class Code(Base):
    html_url: str


@dataclass
class Repository(Base):
    pass


Result = Code | Commit | Repository


def parse(j: Json) -> Result:
    orig_j = j
    # FIXME ugh.. this will still modify due to nested dicts
    j = {k: v for k, v in j.items()}
    print(j.keys())
    entity_types = []
    # FIXME hmm might be easier to add entity type during search?
    if 'path' in j:
        entity_types.append('code')
    if 'commit' in j:
        entity_types.append('commit')
    assert len(entity_types) == 1, (entity_types, j)
    [entity_type] = entity_types

    j['repository'] = {
        # filter out weird 'templates'
        # TODO maybe delete them during scraping
        k: v
        for k, v in j['repository'].items()
        if not isinstance(v, str) or not ('api.github.com' in v and '{' in v and '}' in v)
    }

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
    else:
        raise RuntimeError(entity_type)
