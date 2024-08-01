from dataclasses import dataclass

from ...core.common import datetime_aware
from .model import Result
from ...renderers.markdown import Author, MarkdownAdapterT, make_title


# FIXME move to common?
def reddit(s: str) -> str:
    assert s.startswith('/'), s
    return f'https://reddit.com{s}'


@dataclass
class MarkdownAdapter(MarkdownAdapterT):
    # TODO hmm so there are dupe uids with slightly different descriptions
    # should probably fix them during db insertion...
    # sometimes ups or downs change.. so again no point repeating??
    #
    # TODO hmm often link is posted at multiple subreddits.. dunno
    o: Result  # FIXME maybe rename Result to Model everywhere??

    @property
    def created_at(self) -> datetime_aware:
        return self.o.created_at

    @property
    def author(self) -> Author:
        name = self.o.author_name
        if name is None:
            name = 'DELETED'  # I think it was possible for my old axol version
        return Author(
            domain='reddit.com',
            kind='Reddit',
            name=name,
            url=reddit('/user/' + name),
        )

    # TODO maybe need to put meta (like up/down etc) above
    # otherwise it might get truncated
    @property
    def content(self) -> str:
        o = self.o

        subreddit = f'/r/{o.subreddit_name}'
        ups = f'{o.ups}⇧'  # not really interested in downvotes?
        prefix = f'{ups} {subreddit}'
        title_line = make_title(prefix=prefix, title=o.title, permalink=o.permalink, url=o.url)

        parts: list[str] = []
        footer = ', '.join(parts)

        body = o.selftext_md

        content = '\n'.join([title_line, body, footer])
        return content
