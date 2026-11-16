import re
from dataclasses import dataclass
from typing import assert_never

from ...core.common import datetime_aware
from ...renderers.markdown import Author, MarkdownAdapterT, make_title
from .model import Code, Commit, Issue, Model, Repository


@dataclass
class MarkdownAdapter(MarkdownAdapterT):
    model: Model

    @property
    def created_at(self) -> datetime_aware | None:
        return self.model.created_at

    @property
    def author(self) -> Author:
        user = self.model.user
        if user is None:
            name = 'DELETED'
            url = f'https://github.com/{name}'  # meh
        else:
            name = user.login
            url = user.url
        # Some logins have a bracketed suffix, e.g. 'dependabot[bot]' (GitHub apps), or '<hash>[api]' (ProgrammaticAccessBot).
        # Author names can't contain brackets, so turn the suffix into '_bot'/'_api'.
        # Regular GitHub logins can't contain underscores, so this won't clash with real users.
        # Matching the login rather than the user 'type' field, since many older crawled items don't have 'type'.
        # Also some bots don't have a suffix (e.g. 'Copilot' is type 'Bot'), so renaming by type would change existing names.
        if (m := re.fullmatch(r'(.+)\[(\w+)\]', name)) is not None:
            name = f'{m[1]}_{m[2]}'
        return Author(
            domain='github.com',
            kind='Github',
            name=name,
            url=url,
        )

    @property
    def content(self) -> str:
        o = self.model

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

        content = f'{title_line}\n{body}'
        return content


def test_author_bracketed_login() -> None:
    from datetime import UTC, datetime

    from .model import User

    def author(*, login: str, url: str) -> Author:
        commit = Commit(
            created_at=datetime(2026, 1, 20, 22, 18, tzinfo=UTC),
            html_url='https://github.com/example/repo/commit/916c86db6538d938f6e94375591b356cfdd76e5c',
            user=User(login=login, url=url),
            repo='example/repo',
            message='Update README.md',
        )
        return MarkdownAdapter(commit).author

    # ProgrammaticAccessBot: GitHub reports this html_url for it, even though the page 404s
    api_login = '8a3ce807f6da8ef32e8f5c408e949bd2b5[api]'
    # fmt: off
    for login, url, expected_name in [
        ('karlicoss'      , 'https://github.com/karlicoss'      , 'karlicoss'                             ),
        ('dependabot[bot]', 'https://github.com/apps/dependabot', 'dependabot_bot'                        ),
        (api_login        , f'https://github.com/{api_login}'   , '8a3ce807f6da8ef32e8f5c408e949bd2b5_api'),
    ]:
        assert author(login=login, url=url) == Author(domain='github.com', kind='Github', name=expected_name, url=url)
    # fmt: on
