from dataclasses import dataclass
from datetime import datetime, timezone

from axol.core.common import datetime_aware, Json, _check


@dataclass
class Bookmark:
    slug: str
    created_at: datetime_aware
    author: str
    title: str
    url: str
    tags: tuple[str]
    description: str

    @property
    def permalink(self) -> str:
        # user can be anything
        return f'https://pinboard.in/u:_/b:{self.slug}'


Result = Bookmark


def parse(j: Json) -> Result:
    j = {k: v for k, v in j.items()}

    ignore = [
        'author_id',  # not sure if useful?
        'cached',
        'code',  # http code?
        'id',  # we're using slug instead
        'in_collection',
        'private',
        'sertags',  # like tags but concatenated?
        'snapshot_id',
        'source',  # not sure what is it? some number
        'toread',
        'url_id',
        'url_slug',
        'updated',
        'url_count',  # not sure what is it -- sometimes None sometimes not
        'user_id',
    ]
    for k in ignore:
        j.pop(k, None)

    slug = j.pop('slug')

    # TODO not sure if should normalise tags?
    # e.g. to lowercase
    tags = tuple(sorted(j.pop('tags')))
    author  = _check(j.pop('author')     , str)
    title   = _check(j.pop('title')      , str)
    url     = _check(j.pop('url')        , str)
    descr   = _check(j.pop('description'), str)
    created = _check(j.pop('created')    , str)

    # kinda unclear which timezone is date in
    # but tried fetching page from different machines and it seems the same
    # so I assume utc?
    created_at = datetime.strptime(created, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)

    assert len(j) == 0, j

    return Bookmark(
        slug=slug,
        created_at=created_at,
        author=author,
        title=title,
        url=url,
        tags=tags,
        description=descr,
    )
