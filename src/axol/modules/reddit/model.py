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
    author_name: str | None  # looks like might be none if they deleted themselves?
    downs: int
    ups: int
    _permalink: str
    title: str

    selftext_md: str
    selftext_html: str | None  # can be none for 'link' submission

    @property
    def permalink(self) -> str:
        return _reddit(self._permalink)


Result = Submission


def parse(j: Json) -> Submission:
    ts_utc = j['created_utc']
    created_at = datetime.fromtimestamp(ts_utc, tz=timezone.utc)

    url = j['url']
    # TODO right, so it might actually be direct link to website
    # e.g. https://www.reddit.com/r/hypeurls/comments/10j5iy9/ask_hn_has_anyone_fully_attempted_bret_victors/
    # assert 'https://www.reddit.com/r/' in url, url
    # FIXME add url to Submission object? and use downstream

    selftext_html: str | None = j['selftext_html']
    author_name = j['author']['name']

    from_old_axol = j.get('_from_old_axol', False)
    if not from_old_axol:
        assert isinstance(author_name, str), j

    return Submission(
        id=j['id'],
        created_at     = created_at,
        subreddit_name = _check(j['subreddit']['display_name'], str),
        downs          = _check(j['downs']                    , int),
        ups            = _check(j['ups']                      , int),
        _permalink     = _check(j['permalink']                , str),
        title          = _check(j['title']                    , str),
        selftext_md    = _check(j['selftext']                 , str),
        author_name    = author_name,
        selftext_html  = selftext_html,
    )
