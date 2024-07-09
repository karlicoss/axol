from datetime import datetime
from dataclasses import dataclass
from typing import Any, Sequence, assert_never, cast

from bs4 import BeautifulSoup, NavigableString

from axol.core.common import datetime_aware
from .common import extract_uid
from .query import Kind


@dataclass
class _Base:
    dt: datetime_aware
    id: str
    title: str  # NOTE: this is story title (e.g. for Comment)
    url: str  # NOTE: this is story url (e.g. for Comment)
    author: str

    def permalink(self) -> str:
        # NOTE: in principle could extract permalink from the body, it contains user readable alias as well
        # e.g. https://lobste.rs/s/wmwoc4/userland_dataflow_environment_for_end#c_06ceqk
        # but this works well anyway
        return f'https://lobste.rs/s/{self.id}'


@dataclass
class Story(_Base):
    score: int
    comments: int
    tags: Sequence[str]


@dataclass
class Comment(_Base):
    score: int | None  # score is unavailable if the comment is super new
    text: str


Result = Story | Comment


def parse(data: bytes) -> Result:
    bs = BeautifulSoup(data, 'html.parser')
    [_soup] = bs.children
    soup = cast(Any, _soup)  # ugh. seems like bs4 has wrong type annotations

    kinds: list[Kind] = []
    if 'story' in soup['class']:
        kinds.append('stories')
    if 'comment' in soup['class']:
        kinds.append('comments')
    [kind] = kinds

    eid = extract_uid(soup)

    [score_e] = soup.select('.score')
    score_s = score_e.text.strip()
    score = None if len(score_s) == 0 else int(score_s)

    dt_es = soup.select('.byline span[title*=""]')
    [dt_e] = [x for x in dt_es if 'ago' in x.text]
    dt_s = dt_e.attrs['title']
    dt = datetime.fromisoformat(dt_s)
    assert dt.tzinfo is not None

    if kind == 'stories':
        [title_e] = soup.select('.u-url')
        title = title_e.text
        url = title_e.attrs['href']

        [tags_e] = soup.select('.tags')
        tags = [x.text.strip() for x in tags_e.select('.tag')]

        [comments_e] = soup.select('.mobile_comments')
        comments = int(comments_e.text)

        [author_e] = soup.select('.u-author')
        author = author_e.text

        assert score is not None  # shouldn't happen for stories
        story = Story(
            dt=dt,
            id=eid,
            title=title,
            url=url,
            author=author,
            score=score,
            comments=comments,
            tags=tags,
        )
        return story
    elif kind == 'comments':
        [byline] = soup.select('.byline')
        children = [c for c in byline.children if not isinstance(c, NavigableString)]
        [_, _, info_e, permalink_e, _, story_e, _] = children

        [author_e] = info_e.select('a')[-1]  # meh
        author = author_e.text

        title = story_e.text
        assert len(title) > 0
        url = story_e.attrs['href']
        assert url.startswith('/s/')

        assert permalink_e.text == 'link'
        permalink = permalink_e.attrs['href']

        [text_e] = soup.select('.comment_text')
        comment_text = text_e.text
        assert len(comment_text) > 0

        comment = Comment(
            dt=dt,
            id=eid,
            title=title,
            url=url,
            author=author,
            score=score,
            text=comment_text,
        )
        return comment
    else:
        assert_never(kind)
