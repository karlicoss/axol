from dataclasses import dataclass

from ...core.common import datetime_aware
from .common import pinboard_link
from .model import Result
from ...renderers.markdown import Author, MarkdownAdapterT, make_title


@dataclass
class MarkdownAdapter(MarkdownAdapterT):
    # TODO on the one hand, lots of dupes in pinboard when people bookmark same stuff
    # on the other, when it runs daily gonna be hard to deduplicate?
    # dunno. pinboard is a bit unuque here
    o: Result

    @property
    def created_at(self) -> datetime_aware:
        return self.o.created_at

    @property
    def author(self) -> Author:
        name = self.o.author
        return Author(
            domain='pinboard.in',
            kind='Pinboard',
            name=name,
            url=pinboard_link(f'/u:{name}'),
        )

    # TODO for old html renderer I think I grouped it
    # so for same bookmark, users appeared in a table along with descriptions
    @property
    def content(self) -> str:
        o = self.o

        title_line = make_title(title=o.title, permalink=o.permalink, url=o.url)

        tag_links = []
        for tag in o.tags:
            tag_url = pinboard_link(f'/u:{o.author}/t:{tag}')
            tag_links.append(f'[`#{tag}`]({tag_url})')
        parts = []
        if len(tag_links) > 0:
            parts.append('`tags:` ' + ' '.join(tag_links))
        footer = ', '.join(parts)

        body = o.description or ''

        content = '\n'.join([title_line, body, footer])
        return content
