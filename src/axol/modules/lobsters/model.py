from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from bs4 import BeautifulSoup, NavigableString
from typing_extensions import assert_never

from axol.core.common import datetime_aware, html
from axol.core.compat import fromisoformat

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


Model = Story | Comment


def parse(data: bytes) -> Model:
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

    dt_es = soup.select('.byline span[title*=""], .byline a[title*=""]')
    [dt_e] = [x for x in dt_es if 'ago' in x.text]
    dt_s = dt_e.attrs['title']
    dt = fromisoformat(dt_s)
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
        tags = tuple(x.text.strip() for x in tags_e.select('.tag'))

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

        if len(children) == 7:
            # old style (pre 2025?)
            pass
        elif len(children) == 6:
            # new style -- seems like permalink is now in the datetime element
            children.insert(3, dt_e)
        else:
            raise RuntimeError(f'Unexpected number of children: {children}')

        [
            _a_name_e,
            _comment_folder_e,
            info_e,
            permalink_e,
            _flagger_e,
            story_e,
            _reason_e,
        ] = children

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

        assert permalink_e.text == 'link' or 'ago' in permalink_e.text, permalink_e
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


def test_parse_pre_2025() -> None:
    # older comment (pre-2025?), had slightly different format of username/date line
    data = '''
<div class="comment" data-shortid="jmzgo0" id="c_jmzgo0">
<div class="voters">
<a class="upvoter" href="/login"></a>
<div class="score">2</div>
</div>
<div class="comment_parent_tree_line score_shown no_children"></div>
<div class="details">
<div class="byline">
<a name="c_jmzgo0"></a>
<label class="comment_folder comment_folder_inline force_inline" for="comment_folder_jmzgo0"></label>
<span class="">
<a href="/~roryokane"><img alt="roryokane avatar" class="avatar" decoding="async" height="16" loading="lazy" src="/avatars/roryokane-16.png" srcset="/avatars/roryokane-16.png 1x, /avatars/roryokane-32.png 2x" width="16"/></a>
<a href="/~roryokane">roryokane</a>
<span title="2013-08-02 19:56:57 -0500">10 years ago</span>
</span>

        |
        <a href="/s/ebn03k/future_programming#c_jmzgo0">link</a>
<span class="flagger flagger_stub"></span>


          | on:
          <a href="/s/ebn03k/future_programming">The Future of Programming</a>
<span class="reason">
</span>
</div>
<div aria-level="3" class="comment_text" role="heading">
<p>Link: <a href="http://vimeo.com/36579366" rel="nofollow">Bret Victor - Inventing on Principle</a></p>
</div>
</div>
</div>
'''.strip().encode(
        'utf8'
    )

    res = parse(data)

    assert res == Comment(
        dt=datetime(2013, 8, 2, 19, 56, 57, tzinfo=timezone(timedelta(days=-1, seconds=68400))),
        id='c_jmzgo0',
        title='The Future of Programming',
        url='https://lobste.rs/s/ebn03k/future_programming',
        author='roryokane',
        permalink='https://lobste.rs/s/ebn03k/future_programming#c_jmzgo0',
        score=2,
        text=html(
            html='\n' '<p>Link: <a href="http://vimeo.com/36579366" ' 'rel="nofollow">Bret Victor - Inventing on ' 'Principle</a></p>\n'
        ),
    )


def test_parse_new() -> None:
    data = '''
<div class="comment" data-shortid="a2fpmt" id="c_a2fpmt">
<div class="voters">
<a class="upvoter" href="/login"></a>
<div class="score"> </div>
</div>
<div class="comment_parent_tree_line"></div>
<div class="details">
<div class="byline">
<a name="c_a2fpmt"></a>
<label class="comment_folder comment_folder_inline force_inline" for="comment_folder_a2fpmt"></label>
<span class="">
<a href="/~edk-"><img alt="edk- avatar" class="avatar" decoding="async" height="16" loading="lazy" src="/avatars/edk--16.png" srcset="/avatars/edk--16.png 1x, /avatars/edk--32.png 2x" width="16"/></a>
<a href="/~edk-">edk-</a>
<a href="/s/kj6fts/our_interfaces_have_lost_their_senses#c_a2fpmt" title="2025-03-17 11:53:51 -0500">10 hours ago</a>
</span>
<span class="flagger flagger_stub"></span>


          | on:
          <a href="/s/kj6fts/our_interfaces_have_lost_their_senses">Our interfaces have lost their senses</a>
<span class="reason">
</span>
</div>
<div aria-level="3" class="comment_text" role="heading">
<blockquote>
<p>As far as the status quo HCI paradigm goes, we’ve obviously made a lot of progress over the last 50 years.</p>
</blockquote>
<p>I realise that default bias plays a role in my thinking here, but I feel like we made a lot of progress over the first 20-25 of those years, and then spent the balance making things worse again. Computer UIs now are a confused mix of simulacra orphaned from their desktop metaphor antecedents, screenshot-optimised flat layouts with zero affordances ever, and functionality hidden behind random icons wherever it’ll fit in the name of decluttering.</p>
<p>As for Bret Victor’s post… I have my doubts. Manipulating things by touch isn’t very abstract. Manipulating symbols isn’t very tactile. It sounds a bit quippy to ask “what does a monad feel like?” but if you think screens are inadequate for interacting with them the question should at least in principle be answerable.</p>
</div>
</div>
</div>
'''.strip().encode(
        'utf8'
    )

    res = parse(data)

    assert res == Comment(
        dt=datetime(2025, 3, 17, 11, 53, 51, tzinfo=timezone(timedelta(days=-1, seconds=68400))),
        id='c_a2fpmt',
        title='Our interfaces have lost their senses',
        url='https://lobste.rs/s/kj6fts/our_interfaces_have_lost_their_senses',
        author='edk-',
        permalink='https://lobste.rs/s/kj6fts/our_interfaces_have_lost_their_senses#c_a2fpmt',
        score=None,
        text=html(
            html='\n'
            '<blockquote>\n'
            '<p>As far as the status quo HCI paradigm goes, we’ve '
            'obviously made a lot of progress over the last 50 '
            'years.</p>\n'
            '</blockquote>\n'
            '<p>I realise that default bias plays a role in my '
            'thinking here, but I feel like we made a lot of '
            'progress over the first 20-25 of those years, and then '
            'spent the balance making things worse again. Computer '
            'UIs now are a confused mix of simulacra orphaned from '
            'their desktop metaphor antecedents, '
            'screenshot-optimised flat layouts with zero '
            'affordances ever, and functionality hidden behind '
            'random icons wherever it’ll fit in the name of '
            'decluttering.</p>\n'
            '<p>As for Bret Victor’s post… I have my doubts. '
            'Manipulating things by touch isn’t very abstract. '
            'Manipulating symbols isn’t very tactile. It sounds a '
            'bit quippy to ask “what does a monad feel like?” but '
            'if you think screens are inadequate for interacting '
            'with them the question should at least in principle be '
            'answerable.</p>\n'
        ),
    )
