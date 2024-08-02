from dataclasses import dataclass

from ...core.common import datetime_aware
from .common import reddit_link
from .model import Model
from ...renderers.markdown import Author, MarkdownAdapterT, make_title


@dataclass
class MarkdownAdapter(MarkdownAdapterT):
    # TODO hmm often link is posted at multiple subreddits.. dunno
    model: Model

    @property
    def created_at(self) -> datetime_aware:
        return self.model.created_at

    @property
    def author(self) -> Author:
        name = self.model.author_name
        if name is None:
            name = 'DELETED'  # I think it was possible for my old axol version
        return Author(
            domain='reddit.com',
            kind='Reddit',
            name=name,
            url=reddit_link('/user/' + name),
        )

    # TODO maybe need to put meta (like up/down etc) above
    # otherwise it might get truncated
    @property
    def content(self) -> str:
        o = self.model

        subreddit = f'/r/{o.subreddit_name}'
        ups = f'{o.ups}⇧'  # not really interested in downvotes?
        prefix = f'{ups} {subreddit}'
        title_line = make_title(prefix=prefix, title=o.title, permalink=o.permalink, url=o.url)

        body = o.selftext_md

        content = '\n'.join([title_line, body])
        return content
