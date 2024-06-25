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
    description: str | None

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

    # put to lowercase, since they are treated the same by pinboard
    tags = [t.lower() for t in j.pop('tags')]
    tags = [t for t in tags if len(t) > 0]  # sometimes there is an empty string here

    descr = j.pop('description')  # can be None
    author  = _check(j.pop('author')     , str)
    title   = _check(j.pop('title')      , str)
    url     = _check(j.pop('url')        , str)
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
        tags=tuple(sorted(tags)),
        description=descr,
    )
