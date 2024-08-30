import re
from abc import abstractmethod
from dataclasses import dataclass
from html import unescape as html_unescape
from typing import Any

from ..core.common import datetime_aware, html


@dataclass
class Author:
    domain: str
    kind: str
    name: str
    url: str

    def __post_init__(self) -> None:
        # FIXME need to sanitize/validate properly (have a helper in hpi2zulip)
        # NOTE: can't contain square brackets
        assert re.fullmatch(r'[\w\.-]+', self.name), self
        assert self.url.startswith('http'), self


# TODO hmm mypy is not warning about notimplemented??
class MarkdownAdapterT:
    @abstractmethod
    def __init__(self, model: Any) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def created_at(self) -> datetime_aware | None:
        """
        When item was created (this is different from crawl datetime).
        Sometimes this information isn't available, in this case return None and leave for the consumer to decide what to do.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def author(self) -> Author:
        """
        Typically items have a well defined author, it can be useful for rendering to separate it out from the body
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def content(self) -> str:
        # todo split in header and footer?  or return a dataclass containing them?
        # not sure if there is much benefit tho
        raise NotImplementedError


def from_html(text: html) -> str:
    from html2text import HTML2Text

    html_text = text.html
    htext = html_unescape(html_text)
    converter = HTML2Text(
        bodywidth=1000,  # default in 78
    )
    # by default uses "_"
    # which isn't supported in zulip yet https://github.com/zulip/zulip/issues/12325
    converter.emphasis_mark = '*'
    body = converter.handle(htext)
    return body


# TODO might need to sanitize title
# maybe use some proper md renderer?
# TODO maybe separate title out of body?
def make_title(
    *,
    title: str,
    permalink: str,
    url: str | None,
    prefix: str | None = None,
) -> str:
    # TODO add 'extra', insert before direct url?
    # ugh. kinda confusing, but not sure how to name better
    # permalink is the link to service itself (e.g. reddit/hn)
    # url is the link to the site it's referring to
    assert len(title.strip()) > 0, title  # TODO might be empty for pinboard
    assert '://' in permalink, permalink
    parts = [
        '##',
        *([prefix] if prefix is not None else []),
        f'[{title}]({permalink})',
    ]
    if url is not None:
        assert '://' in url, url
        parts.append(f'    [#]({url})')
    return ' '.join(parts)
