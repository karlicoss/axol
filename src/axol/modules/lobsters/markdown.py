from dataclasses import dataclass


from ...core.common import datetime_aware
from .model import Result, Comment, Story
from ...renderers.markdown import Author, MarkdownAdapterT, from_html, make_title


@dataclass
class MarkdownAdapter(MarkdownAdapterT):
    o: Result

    @property
    def created_at(self) -> datetime_aware:
        return self.o.dt

    @property
    def author(self) -> Author:
        # TODO not sure if should remove author from body?
        # although if it's on the same line doesn't hurt?
        # maybe just reuse Author object
        name = self.o.author
        return Author(
            domain='lobste.rs',
            kind='Lobsters',
            name=name,
            url=f'https://lobste.rs/~{name}',
        )

    # TODO instead yield lines for the downstream to join?
    # TODO check for unused properties?
    @property
    def content(self) -> str:
        o = self.o

        prefix = None if o.score is None else f'{o.score}⇧'
        title_line = make_title(prefix=prefix, title=o.title, permalink=o.permalink, url=o.url)

        if isinstance(o, Comment):
            title_line += ' : comment'

        parts = []
        if isinstance(o, Story):
            tagss = ' '.join(f'#{t}' for t in o.tags)
            parts.append(f'`tags: {tagss}`')
        footer = ', '.join(parts)

        body = ''
        if isinstance(o, Comment):
            # Story doesn't have any text snippet
            body = from_html(o.text)

        content = '\n'.join([title_line, body, footer])
        return content
