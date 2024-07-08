from datetime import datetime
from dataclasses import dataclass
from typing import Any, Sequence, assert_never, cast

from bs4 import BeautifulSoup, NavigableString

from axol.core.common import datetime_aware
from .query import Kind


@dataclass
class Story:
    dt: datetime_aware
    id: str
    title: str
    url: str
    score: int
    comments: int
    tags: Sequence[str]
    author: str
    # permalink: str  # FIXME should just be property? idk


@dataclass
class Comment:
    dt: datetime_aware
    id: str
    title: str
    url: str
    author: str
    permalink: str
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

    eid = soup.attrs['data-shortid']

    [score_e] = soup.select('.score')
    score = int(score_e.text)

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

        story = Story(
            dt=dt,
            id=eid,
            title=title,
            url=url,
            score=score,
            comments=comments,
            tags=tags,
            author=author,
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
            permalink=permalink,
            text=comment_text,
        )
        return comment
    else:
        assert_never(kind)
