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

    [score_e] = soup.select('.voters')
    score_s = score_e.text.strip()
    score: int | None = None
    try:
        score = int(score_s)
    except ValueError:
        # for very new comments score isn't defined
        # it used to be just empty string, but seems like now it's ~ or something like that?
        # seems easiest to just be defensive
        pass

    dt_es = soup.select('.byline span[title*=""], .byline a[title*=""], .byline time[title*=""]')
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
            [
                _a_name_e,
                _comment_folder_e,
                info_e,
                permalink_e,
                _flagger_e,
                story_e,
                _reason_e,
            ] = children
        elif len(children) == 6:
            # new style -- seems like permalink is now in the datetime element
            [
                _a_name_e,
                _comment_folder_e,
                info_e,
                _flagger_e,
                story_e,
                _reason_e,
            ] = children
            permalink_e = dt_e
        elif len(children) == 5:
            # new format somewhere around may 2025?
            [
                _a_name_e,
                info_e,
                _flagger_e,
                story_e,
                _reason_e,
            ] = children
            # ugh, they removed full permalink from html.. only keeping something like https://lobste.rs/c/ie6oqd
            # so now have to construct full one manually (below)
            permalink_e = None
        elif len(children) == 4:
            [
                info_e,
                _flagger_e,
                story_e,
                _reason_e,
            ] = children
            permalink_e = None
        else:
            raise RuntimeError(f'Unexpected number of children: {children}')

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

        if permalink_e is not None:
            assert permalink_e.text == 'link' or 'ago' in permalink_e.text, permalink_e
            permalink = permalink_e.attrs['href']
        else:
            permalink = f'{url}#{eid}'
        permalink = lobsters_link(permalink)

        url = lobsters_link(url)

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
'''.strip().encode('utf8')

    res = parse(data)

    assert res == Comment(
        dt=datetime(2013, 8, 2, 19, 56, 57, tzinfo=timezone(timedelta(days=-1, seconds=68400))),
        id='c_jmzgo0',
        title='The Future of Programming',
        url='https://lobste.rs/s/ebn03k/future_programming',
        author='roryokane',
        permalink='https://lobste.rs/s/ebn03k/future_programming#c_jmzgo0',
        score=2,
        text=html(html='\n<p>Link: <a href="http://vimeo.com/36579366" rel="nofollow">Bret Victor - Inventing on Principle</a></p>\n'),
    )


def test_parse_new_1() -> None:
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
</div>
</div>
</div>
'''.strip().encode('utf8')

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
        ),
    )


def test_parse_story_new_2() -> None:
    """
    Somewhere around 2025?
    - class="score" is not present anymore and score is directly under "upvoter"?
    - post datetime is now under <time> tag
    """
    data = '''
<li class="story" data-shortid="r9tamc" id="story_r9tamc">
<div class="story_liner h-entry">
<div class="voters">
<a class="upvoter" href="/login">3</a>
</div>
<div class="details">
<span aria-level="1" class="link h-cite u-repost-of" role="heading">
<a class="u-url" href="https://www.infocentral.org/" rel="ugc noreferrer">An Architectural Approach to Decentralization</a>
</span>
<span class="tags">
<a class="tag tag_distributed" href="/t/distributed" title="Distributed systems">distributed</a>
<a class="tag tag_ai" href="/t/ai" title="Developing artificial intelligence, machine learning. Tag AI usage only with `vibecoding`.">ai</a>
</span>
<a class="domain" href="/domains/infocentral.org">infocentral.org</a>
<div class="byline">
<a href="/~schmudde"><img alt="schmudde avatar" class="avatar" decoding="async" height="16" loading="lazy" src="/avatars/schmudde-16.png" srcset="/avatars/schmudde-16.png 1x, /avatars/schmudde-32.png 2x" width="16"/></a>
<span> via </span>
<a class="u-author h-card" href="/~schmudde">schmudde</a>
<time datetime="2025-06-16 03:54:44-0500" title="2025-06-16 03:54:44 -0500">18 hours ago</time>
<span> | </span>
<span class="dropdown_parent">
<input class="archive_button" id="archive_r9tamc" type="checkbox"/>
<label for="archive_r9tamc" tabindex="0">caches</label>
<div class="archive-dropdown">
<a href="https://web.archive.org/web/3/https%3A%2F%2Fwww.infocentral.org%2F">Archive.org</a>
<a href="https://archive.today/https%3A%2F%2Fwww.infocentral.org%2F">Archive.today</a>
<a href="https://ghostarchive.org/search?term=https%3A%2F%2Fwww.infocentral.org%2F">Ghostarchive</a>
</div>
</span>
<span class="comments_label">
<span> | </span>
<a aria-level="2" href="/s/r9tamc/architectural_approach" role="heading">
              no comments</a>
</span>
</div>
</div>
</div>
<a class="mobile_comments zero" href="/s/r9tamc/architectural_approach" style="display: none;">
<span>0</span>
</a>
</li>
'''.strip().encode('utf8')

    res = parse(data)
    assert res == Story(
        dt=datetime(2025, 6, 16, 3, 54, 44, tzinfo=timezone(timedelta(days=-1, seconds=68400))),
        id='r9tamc',
        title='An Architectural Approach to Decentralization',
        url='https://www.infocentral.org/',
        author='schmudde',
        permalink='https://lobste.rs/s/r9tamc/architectural_approach',
        score=3,
        comments=0,
        tags=('distributed', 'ai'),
    )


def test_parse_comment_new_2() -> None:
    data = '''
<div class="comment" data-shortid="mtfz3s" id="c_mtfz3s">
<div class="voters">
<label class="comment_folder" for="comment_folder_mtfz3s"></label>
<a class="upvoter" href="/login">3</a>
</div>
<div class="details">
<div class="byline">
<a name="c_mtfz3s"></a>
<span class="">
<a href="/~madhadron"><img alt="madhadron avatar" class="avatar" decoding="async" height="16" loading="lazy" src="/avatars/madhadron-16.png" srcset="/avatars/madhadron-16.png 1x, /avatars/madhadron-32.png 2x" width="16"/></a>
<a href="/~madhadron">madhadron</a>
<a href="/c/mtfz3s"><time datetime="2025-05-23 17:33:09-0500" title="2025-05-23 17:33:09 -0500">3 days ago</time></a>
</span>
<span class="flagger flagger_stub"></span>


          | on:
          <a href="/s/faowua/spaced_repetition_systems_have_gotten">Spaced Repetition Systems Have Gotten Way Better</a>
<span class="reason">
</span>
</div>
<div aria-level="3" class="comment_text" role="heading">
<p>Thereâs several pieces to effective language learning, and Anki is one of them.</p>
</div>
</div>
</div>
'''.strip().encode('utf8')

    res = parse(data)
    assert res == Comment(
        dt=datetime(2025, 5, 23, 17, 33, 9, tzinfo=timezone(timedelta(days=-1, seconds=68400))),
        id='c_mtfz3s',
        title='Spaced Repetition Systems Have Gotten Way Better',
        url='https://lobste.rs/s/faowua/spaced_repetition_systems_have_gotten',
        author='madhadron',
        permalink='https://lobste.rs/s/faowua/spaced_repetition_systems_have_gotten#c_mtfz3s',
        score=3,
        text=html(html='\n<p>Thereâs several pieces to effective language learning, and Anki is one of them.</p>\n'),
    )


def test_parse_comment_new_3() -> None:
    data = '''
<div class="comment" data-shortid="6uarnf" id="c_6uarnf">
<label class="comment_folder" for="comment_folder_6uarnf"></label>
<div class="comment_gutter">
<div class="voters">
<a class="upvoter" href="/login"></a>
</div>
</div>
<div class="details">
<div class="byline">
<span class="">
<a href="/~andyc"><img alt="andyc avatar" class="avatar" decoding="async" height="16" loading="lazy" src="/avatars/andyc-16.png" srcset="/avatars/andyc-16.png 1x, /avatars/andyc-32.png 2x" width="16"/></a>
<a href="/~andyc">andyc</a>


            edited
            <a href="/c/6uarnf" title="2025-05-08 18:17:59 -0500">3 hours ago</a>
</span>
<span class="flagger flagger_stub"></span>


          | on:
          <a href="/s/xnyrve/memory_safety_features_zig">Memory Safety Features in Zig</a>
<span class="reason">
</span>
</div>
<div aria-level="3" class="comment_text" role="heading">
<p>Thank you for being precise about the terminology – seg faults are indeed a mechanism to <strong>enforce</strong> memory safety.</p>
</div>
</div>
</div>
'''.strip().encode('utf8')

    res = parse(data)
    assert res == Comment(
        dt=datetime(2025, 5, 8, 18, 17, 59, tzinfo=timezone(timedelta(days=-1, seconds=68400))),
        id='c_6uarnf',
        title='Memory Safety Features in Zig',
        url='https://lobste.rs/s/xnyrve/memory_safety_features_zig',
        author='andyc',
        permalink='https://lobste.rs/s/xnyrve/memory_safety_features_zig#c_6uarnf',
        score=None,
        text=html(
            html='\n'
            '<p>Thank you for being precise about the terminology – '
            'seg faults are indeed a mechanism to '
            '<strong>enforce</strong> memory safety.</p>\n'
        ),
    )
