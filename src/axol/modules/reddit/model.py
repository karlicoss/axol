from dataclasses import dataclass
from datetime import datetime, timezone

import orjson

from axol.core.common import _check, datetime_aware

from .common import reddit_link


@dataclass
class Submission:
    id: str
    created_at: datetime_aware
    subreddit_name: str
    author_name: str | None  # looks like might be none if they deleted themselves?
    downs: int
    ups: int
    _permalink: str
    title: str

    # usually just a reddit link
    # but sometimes contains direct link to the site
    # e.g. https://www.reddit.com/r/hypeurls/comments/10j5iy9/ask_hn_has_anyone_fully_attempted_bret_victors/
    url: str

    selftext_md: str
    selftext_html: str | None  # can be none for 'link' submission

    @property
    def permalink(self) -> str:
        return reddit_link(self._permalink)


Model = Submission


def parse(data: bytes) -> Model:
    j = orjson.loads(data)

    ts_utc = j['created_utc']
    created_at = datetime.fromtimestamp(ts_utc, tz=timezone.utc)

    selftext_html: str | None = j['selftext_html']
    author_name: str | None = j['author']['name']

    from_old_axol = j.get('_from_old_axol', False)
    if not from_old_axol:
        assert isinstance(author_name, str), j

    url = _check(j['url'], str)
    if url.startswith('/r'):
        url = reddit_link(url)

    # fmt: off
    return Submission(
        id=j['id'],
        created_at     = created_at,
        subreddit_name = _check(j['subreddit']['display_name'], str),
        downs          = _check(j['downs']                    , int),
        ups            = _check(j['ups']                      , int),
        _permalink     = _check(j['permalink']                , str),
        title          = _check(j['title']                    , str),
        selftext_md    = _check(j['selftext']                 , str),
        url            = url,
        author_name    = author_name,
        selftext_html  = selftext_html,
    )
    # fmt: on
