from dataclasses import dataclass

from ...core.common import datetime_aware
from .common import lobsters_link
from .model import Model, Comment, Story
from ...renderers.markdown import Author, MarkdownAdapterT, from_html, make_title


@dataclass
class MarkdownAdapter(MarkdownAdapterT):
    model: Model

    @property
    def created_at(self) -> datetime_aware:
        return self.model.dt

    @property
    def author(self) -> Author:
        name = self.model.author
        return Author(
            domain='lobste.rs',
            kind='Lobsters',
            name=name,
            url=lobsters_link(f'/~{name}'),
        )

    # TODO instead yield lines for the downstream to join?
    # todo check for unused properties?
    @property
    def content(self) -> str:
        o = self.model

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
