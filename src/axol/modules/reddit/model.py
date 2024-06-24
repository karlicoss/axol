from dataclasses import dataclass
from datetime import datetime, timezone

from axol.core.common import datetime_aware, Json, _check


def _reddit(s: str) -> str:
    return f'https://reddit.com{s}'


@dataclass
class Submission:
    id: str
    created_at: datetime_aware
    subreddit_name: str
    author_name: str  # TODO optional if they deleted themselves?
    downs: int
    ups: int
    _permalink: str
    title: str

    selftext_md: str
    selftext_html: str

    @property
    def permalink(self) -> str:
        return _reddit(self._permalink)


Result = Submission


def parse(j: Json) -> Submission:
    ts_utc = j['created_utc']
    created_at = datetime.fromtimestamp(ts_utc, tz=timezone.utc)

    url = j['url']
    assert 'https://www.reddit.com/r/' in url, url

    return Submission(
        id=j['id'],
        created_at     = created_at,
        subreddit_name = _check(j['subreddit']['display_name'], str),
        author_name    = _check(j['author']['name']           , str),
        downs          = _check(j['downs']                    , int),
        ups            = _check(j['ups']                      , int),
        _permalink     = _check(j['permalink']                , str),
        title          = _check(j['title']                    , str),
        selftext_md    = _check(j['selftext']                 , str),
        selftext_html  = _check(j['selftext_html']            , str),
    )
