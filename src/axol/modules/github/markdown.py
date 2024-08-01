from dataclasses import dataclass
from typing import assert_never

from ...core.common import datetime_aware
from .model import Result, Code, Commit, Issue, Repository
from ...renderers.markdown import Author, MarkdownAdapterT, make_title


@dataclass
class MarkdownAdapter(MarkdownAdapterT):
    o: Result

    # TODO ok, so old uids beepb00p.xyz it's not so unique...
    # TODO hmm so this uid is sort of a repo name + relative path..
    # what happens if there are multiple results for the same file?
    # deal with it later I suppose

    @property
    def created_at(self) -> datetime_aware | None:
        return self.o.created_at

    @property
    def author(self) -> Author:
        user = self.o.user
        if user is None:
            name = 'DELETED'
            url = f'https://github.com/{name}'  # meh
        else:
            name = user.login
            url = user.url
        name = name.replace('[bot]', '_bot')  # meh
        return Author(
            domain='github.com',
            kind='Github',
            name=name,
            url=url,
        )

    @property
    def content(self) -> str:
        o = self.o

        # FIXME hmm need to sanitize the title.. might contain underscores etc
        # should use a proper md renderer I think
        if isinstance(o, Code):
            # TODO ugh. code really has nothing to display?
            # not sure how useful really...
            title = f'code: {o.repo}: {o.path}'
        elif isinstance(o, Commit):
            title = f'commit: {o.repo}'
        elif isinstance(o, Issue):
            title = f'issue: {o.repo}: {o.title}'
        elif isinstance(o, Repository):
            title = f'repository: {o.repo}'
        else:
            assert_never(o)

        prefix: str | None = None
        if isinstance(o, Repository):
            if o.stars > 0:
                prefix = f'{o.stars}☆'

        title_line = make_title(prefix=prefix, title=title, permalink=o.html_url, url=None)
        # TODO will permalink include line number??

        parts: list[str] = []
        footer = ', '.join(parts)

        description: str | None
        if isinstance(o, Code):
            description = None
        elif isinstance(o, Commit):
            description = o.message
        elif isinstance(o, Issue):
            description = o.body
        elif isinstance(o, Repository):
            description = o.description

        body = ''
        if description is not None:
            # NOTE: looks like it's already markdown
            body += description

        content = '\n'.join([title_line, body, footer])
        return content
