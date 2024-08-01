from dataclasses import dataclass

from ...core.common import datetime_aware
from .model import Result, Comment, Story
from ...renderers.markdown import Author, MarkdownAdapterT, from_html, make_title


# TODO should probably return a typed dict which is ready to be converted in message?
# not sure
@dataclass
class MarkdownAdapter(MarkdownAdapterT):
    model: Result

    @property
    def created_at(self) -> datetime_aware:
        return self.model.created_at

    @property
    def author(self) -> Author:
        name = self.model.author
        return Author(
            domain='news.ycombinator.com',
            kind='Hackernews',
            name=name,
            # FIXME move to common for hn? same with domain
            url=f'https://news.ycombinator.com/user?id={name}',
        )

    @property
    def content(self) -> str:
        o = self.model

        if isinstance(o, Comment):
            title = 'comment'
            url = None
        else:
            title = o.title
            url = o.url

        pparts = []
        if isinstance(o, Story):
            if o.points > 0:
                pparts.append(f'{o.points}⇧')
            if o.num_comments > 0:
                pparts.append(f'{o.num_comments}🗨')
        prefix = None if len(pparts) == 0 else ' '.join(pparts)
        title_line = make_title(prefix=prefix, title=title, permalink=o.permalink, url=url)

        # FIXME get rid of footer?
        parts: list[str] = []
        footer = ', '.join(parts)

        body = '' if o.text is None else from_html(o.text)

        content = '\n'.join([title_line, body, footer])
        # TODO could add emoji if it has comments/upvotes etc?
        # yeah, e.g. each provider could decorate somehow? maybe according to percentile?
        # e.g. 90+ % -- fire emoji or something
        return content
