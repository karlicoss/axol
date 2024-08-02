from datetime import datetime
from dataclasses import dataclass
from typing import Any, Sequence, assert_never, cast

from bs4 import BeautifulSoup, NavigableString

from axol.core.common import datetime_aware, html
from .common import extract_uid, lobsters_link
from .query import Kind


@dataclass
class _Base:
    dt: datetime_aware
    id: str
    title: str  # NOTE: this is story title (e.g. for Comment)
    url: str  # NOTE: this is story url (e.g. for Comment)
    author: str
    permalink: str

    # NOTE: f'https://lobste.rs/s/{self.id}' works as well
    # but permalink extracted from html has nicer human readable link


@dataclass
class Story(_Base):
    score: int
    comments: int
    tags: Sequence[str]


@dataclass
class Comment(_Base):
    score: int | None  # score is unavailable if the comment is super new
    text: html


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
    score: int | None = None
    try:
        score = int(score_s)
    except ValueError:
        # for very new comments score isn't defined
        # it used to be just empty string, but seems like now it's ~ or something like that?
        # seems easiest to just be defensive
        pass

    dt_es = soup.select('.byline span[title*=""]')
    [dt_e] = [x for x in dt_es if 'ago' in x.text]
    dt_s = dt_e.attrs['title']
    dt = datetime.fromisoformat(dt_s)
    assert dt.tzinfo is not None

    if kind == 'stories':
        [title_e] = soup.select('.u-url')
        title = title_e.text
        url = title_e.attrs['href']

        if url.startswith('/s/'):
            # weird, sometimes can be a relative url?
            url = lobsters_link(url)
        # eh, sometimes can be HTTPS://?
        assert url.lower().startswith('http'), url

        [tags_e] = soup.select('.tags')
        tags = [x.text.strip() for x in tags_e.select('.tag')]

        [comments_e] = soup.select('.mobile_comments')
        comments = int(comments_e.text)

        permalink = comments_e['href']
        permalink = lobsters_link(permalink)

        [author_e] = soup.select('.u-author')
        author = author_e.text

        assert score is not None  # shouldn't happen for stories
        story = Story(
            dt=dt,
            id=eid,
            title=title,
            url=url,
            author=author,
            permalink=permalink,
            score=score,
            comments=comments,
            tags=tags,
        )
        return story
    elif kind == 'comments':
        [byline] = soup.select('.byline')
        children = [c for c in byline.children if not isinstance(c, NavigableString)]
        [_, _, info_e, permalink_e, _, story_e, _] = children

        # first link in info_e is avatar
        # then actual user link
        # then possible to have some sort of user flair
        author_e = info_e.select('a')[1]
        author = author_e.text
        author_href = author_e['href']
        assert author_href == f'/~{author}', info_e  # validate just in case

        title = story_e.text
        assert len(title) > 0
        url = story_e.attrs['href']
        assert url.startswith('/s/')
        url = lobsters_link(url)

        assert permalink_e.text == 'link'
        permalink = permalink_e.attrs['href']
        permalink = lobsters_link(permalink)

        [text_e] = soup.select('.comment_text')
        assert len(text_e.text) > 0, text_e  # just in case
        comment_text = html(html=text_e.decode_contents())

        comment = Comment(
            dt=dt,
            id=eid,
            title=title,
            url=url,
            author=author,
            permalink=permalink,
            score=score,
            text=comment_text,
        )
        return comment
    else:
        assert_never(kind)
