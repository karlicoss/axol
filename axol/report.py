#!/usr/bin/env python3
import argparse
import re
import sys
import logging
import warnings
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from itertools import islice, chain
from pathlib import Path
from pprint import pprint
from subprocess import check_call, check_output
from typing import (Any, Dict, Iterator, List, NamedTuple, Optional, Sequence,
                    Tuple, Type, Union, Mapping)

from .core.common import classproperty, the
from .core.kdominate import adhoc_html

from .common import logger
from .storage import Changes, get_digest, get_result_type
from .trait import AbsTrait, pull
from .traits import ForReach, ForSpinboard, ForTentacle, ForTwitter, ForHackernews, IgnoreTrait, ignore_result, For

import dominate
import dominate.tags as T
from dominate.util import raw, text
from more_itertools import flatten

from config import DATABASES

from functools import cached_property
cproperty = cached_property # meh, some legacy uses



# TODO need some sort of starting_from??
# TODO I guess just use datetime?


Htmlish = Union[str, T.dom_tag]

STYLE = (Path(__file__).parent / 'css/style.css').read_text()

# TODO use Genetic[T]??

# TODO hmm. maybe calling base class method pulls automatically??
class FormatTrait(AbsTrait):
    @classmethod
    def format(trait, obj, *args, **kwargs) -> Htmlish:
        raise NotImplementedError

    @classmethod
    def title(cls, objs):
        return max((o.title for _, o in objs), key=lambda t: 0 if t is None else len(t))

    @classmethod
    def link(cls, objs):
        return the(o.link  for _, o in objs)

    @classmethod
    def format_one(cls, obj):
        return cls.format([(None, obj)]) # TODO ?

format_result = pull(FormatTrait.format)


def isempty(s) -> bool:
    if s is None:
        return True
    if len(s.strip()) == 0:
        return True
    return False


# TODO not sure if I want DOW
def fdate(d: datetime) -> str:
    return d.strftime('%d %b %Y %H:%M')



# TODO not sure if should inherit from trait... it's more of an impl..
class SpinboardFormat(ForSpinboard, FormatTrait):
    @staticmethod
    def plink(user=None, tag=None) -> str:
        ll = f'https://pinboard.in'
        if user is not None:
            ll += f'/u:{user}'
        if tag is not None:
            ll += f'/t:{tag}'
        return ll

    @classmethod
    def tag_link(cls, tag: str, user=None):
        ll = cls.plink(tag=tag, user=user)
        return T.a(f'#{tag}', href=ll, cls='tag')

    @classmethod
    def user_link(cls, user: str):
        ll = cls.plink(user=user)
        return T.a(user, href=ll, cls='user')

    # TODO default formatter?
    # TODO Self ?? maybe it should be metaclass or something?
    @classmethod
    def format(trait, objs, *args, **kwargs) -> Htmlish:
        # TODO would be nice to have spinboard imported here for type checking..
        res = T.div(cls='pinboard')

        title = trait.title(objs)
        link = trait.link(objs)
        res.add(T.div(T.a(title, href=link)))

        with adhoc_html('pinboard', cb=lambda children: res.add(*children)):
            with T.table():
                for _, obj in objs:
                    if not isempty(obj.description):
                        with T.tr():
                            with T.td(colspan=3):
                                T.span(obj.description, cls='description')
                    with T.tr():
                        # TODO wtf is min??
                        with T.td(cls='min'):
                            T.a(f'{fdate(obj.when)}', href=obj.blink, cls='permalink timestamp')
                        with T.td(cls='min'):
                            text('by ')
                            trait.user_link(user=obj.user)
                        with T.td():
                            for t in obj.ntags:
                                trait.tag_link(tag=t, user=obj.user)
        # TODO userstats
        return res

def reddit(s):
    return f'https://reddit.com{s}'

class ReachFormat(ForReach, FormatTrait):

    @classmethod
    def subreddit_link(cls, sub: str):
        subreddit_link = reddit('/r/' + sub)
        return T.a(sub, href=subreddit_link, cls='subreddit')

    @classmethod
    def user_link(cls, user: str):
        ll = reddit('/u/' + user)
        return T.a(user, href=ll, cls='user')

    @classmethod
    def format(trait, objs, *args, **kwargs) -> Htmlish:
        res = T.div(cls='reddit')

        title = trait.title(objs)
        link = trait.link(objs)

        ll = reddit(link)

        res.add(T.div(T.a(title, href=ll)))
        with adhoc_html('reddit', cb=lambda ch: res.add(*ch)):
            for _, obj in objs:
                if not isempty(obj.description):
                    T.div(obj.description)
                T.div(trait.subreddit_link(obj.subreddit))
                with T.div():
                    ud = f'{obj.ups}⇅{obj.downs}' # TODO sum all ups and downs??
                    T.b(ud)
                    T.a(f'{obj.when.strftime("%Y-%m-%d %H:%M")}', href=ll, cls='permalink')
                    text(' by ')
                    trait.user_link(user=obj.user)
        return res

class TentacleTrait(ForTentacle, FormatTrait):
    # TODO mm. maybe permalink is a part of trait?

    @classmethod
    def user_link(cls, user: str):
        return T.a(user, href=f'https://github.com/{user}', cls='user')

    @classmethod
    def format(trait, objs, *args, **kwargs) -> Htmlish:
        res = T.div(cls='github')
        res.add(T.div(T.a(trait.title(objs), href=trait.link(objs))))
        # TODO total stars?
        with adhoc_html('github', cb=lambda ch: res.add(*ch)):
            for _, obj in objs:
                if not isempty(obj.description):
                    T.div(obj.description)
                with T.div():
                    if obj.stars > 0:
                        sts = '' if obj.stars == 1 else str(obj.stars)
                        T.b(sts + '★')
                    T.a(f'{obj.when.strftime("%Y-%m-%d %H:%M")} by {obj.user}', href=obj.link, cls='permalink')
        return res
        # TODO indicate how often is user showing up?

def tw(s: str) -> str:
    if s.startswith('http'):
        return s
    else:
        # todo not sure if needed?
        return f'https://twitter.com{s}'


class FormatTwitter(ForTwitter, FormatTrait):
    @classmethod
    def user_link(cls, user: str):
        return T.a(user, href=tw('/' + user))

    @classmethod
    def format(trait, objs) -> Htmlish:
        res = T.div(cls='twitter')
        # res.add(T.div(T.a(trait.title(objs), href=tw(trait.link(objs)))))
        with adhoc_html('twitter', cb=lambda ch: res.add(*ch)):
            for _, obj in objs:
                T.div(obj.text)
                with T.div():
                    if obj.likes + obj.retweets + obj.replies > 0:
                        ll = f'★{obj.likes} ♺{obj.retweets} 🗬{obj.replies}'
                        T.b(ll)
                    T.a(
                        f'{obj.when.strftime("%Y-%m-%d %H:%M")} by {obj.user}',
                        href=tw(obj.link),
                        cls='permalink',
                    )
                    T.a('X', user=obj.user, cls='blacklist')
        return res

def hn(s):
    return f'https://news.ycombinator.com{s}'

class FormatHackernews(ForHackernews, FormatTrait):
    @classmethod
    def user_link(cls, user: str):
        return T.a(user, href=hn(f'/user?id={user}'), cls='user')

    @classmethod
    def format(trait, objs) -> Htmlish:
        res = T.div(cls='hackernews')
        with adhoc_html('hackernews', cb=lambda ch: res.add(*ch)):
            for _, obj in objs:
                if obj.url is not None:
                    T.div(T.a(obj.title, href=obj.url))
                T.div(raw(obj.text), cls='text') # eh, it's html
                with T.div():
                    extra = []
                    if obj.points > 0:
                        extra.append(f'🠅{obj.points}')
                    if obj.comments > 0:
                        extra.append(f'🗬{obj.comments}')
                    T.b(' '.join(extra))
                    T.a(
                        obj.when.strftime('%Y-%m-%d %H:%M'),
                        href=obj.link,
                        cls='permalink', # TODO FIXME not sure if should use 'timestamp' class??
                    )
                    text(' by ')
                    trait.user_link(user=obj.user)
        return res


FormatTrait.reg(ReachFormat, SpinboardFormat, TentacleTrait, FormatTwitter, FormatHackernews)


# TODO hmm. instead percentile would be more accurate?...
def get_user_stats(jsons, rtype=None):
    cc = Collector()
    for jj in jsons:
        rev, dd, j = jj
        items = list(map(lambda x: from_json(rtype, x), j))
        cc.register(items)
    cnt = Counter([i.user for i in cc.items.values()])
    total = max(sum(cnt.values()), 1)
    return {
        u: v / total for u, v in cnt.items()
    }

# TODO search is a bit of flaky: initially I was getting
# so like exact opposites
# I guess removed links are basically not interesting, so we want to track whatever new was added

import requests
def send(subject: str, body: str, html=False):
    maybe_html: Dict[str, str] = {}
    if html:
        body = body.replace('\n', '\n<br>')
        maybe_html = {'html': body}
    return requests.post(
        "https://api.mailgun.net/v3/***REMOVED***.mailgun.org/messages",
        auth=(
            "api",
            "***REMOVED***" # TODO secrets..
        ),
        data={"from": "spinboard <mailgun@***REMOVED***.mailgun.org>",
              "to": ["karlicoss@gmail.com"],
              "subject": f"Spinboard stats for {subject}",
              # "text": body,
              **maybe_html,
        }
    )


JS = (Path(__file__).parent / 'js/report.js').read_text()


#
# ok. fuck iframe for now. it doesn't work well.
#
# window.addEventListener('DOMContentLoaded', async (event) => {
#     console.log('DOM fully loaded and parsed');
#
#     const fr = document.createElement('iframe'); document.body.appendChild(fr);
#     fr.src = '';
#     fr.id = 'blacklist';
#
#
#     fr.contentWindow.document.write(`
#     <html>
#     <head>
#     <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.2/codemirror.min.js"></script>
#     </head>
#     <body>
#
#     <div>HELOOO</div>
#     <textarea rows="5" id="bll"></textarea>
#
#     </body></html>
# `);
#
# });

from .core.common import group_by_key

# TODO shit. should use promnesia.cannon instead??
# maybe promnesia could also return if it recognized the URL 'completely' or just guessed
from .core.kurl import normalise

from functools import lru_cache
from collections import Counter

def vote(l):
    data = Counter(l)
    return data.most_common()[0][0]

# TODO kython??
# TODO tests next to function kinda like rust
def invkey(kk):
    from functools import cmp_to_key
    def icmp(a, b):
        ka = kk(a)
        kb = kk(b)
        if ka < kb:
            return 1
        elif ka > kb:
            return 1
        else:
            return 0
    return cmp_to_key(icmp)


# todo jeez.. why did that happen??

def when_key_tz_hack(x):
    when: datetime = x.when
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
        # TODO warn?
    return when


class CumulativeBase(AbsTrait):
    def __init__(self, items: List) -> None:
        self.items = items

    @classproperty
    def FTrait(cls):
        return FormatTrait.for_(cls.Target)

    @cproperty
    def nlink(self) -> str:
        return normalise(self.items[0].link) # TODO not sure if useful..

    @property # type: ignore
    @lru_cache()
    def link(self) -> str:
        return vote(i.link for i in self.items)

    @property # type: ignore
    @lru_cache()
    def when(self) -> str:
        return min(x.when for x in self.items)

    @classproperty
    def cumkey(cls):
        raise NotImplementedError

    @classproperty
    def sortkey(cls):
        raise NotImplementedError

    @classmethod
    def sources_summary(cls, items):
        return f"No sources summary for {cls.Target} yet"

    @classmethod
    def sources_stats(cls, items, key):
        c = Counter()
        for i in items:
            kk = key(i)
            if not isinstance(kk, list):
                kk = [kk]
            for k in kk:
                c[k] += 1
        return list(sorted(c.items(), key=lambda p: (p[1], p[0])))

class SpinboardCumulative(ForSpinboard, CumulativeBase):
    @classproperty
    def cumkey(cls):
        # TODO FIXME reuse grouping code? it could also normalise..
        return lambda x: normalise(x.link)

    @classproperty
    def sortkey(cls):
        return invkey(lambda c: c.when)

    # TODO shit, each of them is gonna require something individual??
    @property # type: ignore
    @lru_cache()
    def tags(self) -> List[str]:
        tt = {x for x in sum((i.ntags for i in self.items), [])}
        return list(sorted(tt))

    @property # type: ignore
    @lru_cache()
    def description(self) -> str:
        return vote(i.description for i in self.items)

    @property # type: ignore
    @lru_cache()
    def title(self) -> str:
        return vote(i.title for i in self.items)

    @property # type: ignore
    @lru_cache()
    def users(self) -> List[str]:
        uu = {x.user for x in self.items}
        return list(sorted(uu))

    def format(self):
        # TODO errr.. why is this duplicated??
        # TODO also display total count??
        # TODO accumulated tags?
        # return self.FTrait.format_one(self.items[0])

        res = T.div(cls='pinboard')
        res.add(T.a(self.title, href=self.link))
        res.add(T.br())
        if not isempty(self.description):
            res.add(self.description)
            res.add(T.br())
        res.add('tags: ')
        for t in self.tags:
            res.add(self.FTrait.tag_link(tag=t))
        res.add(T.br())
        pl = T.div(f'{fdate(self.when)} by', cls='permalink')
        fusers = [self.FTrait.user_link(user=u) for u in self.users]
        for f in fusers:
            pl.add(T.span(f))
        res.add(pl)
        return res

    @classmethod
    def sources_summary(cls, items):
        res = T.div()
        res.add(T.div(T.b('Tag summary:')))
        for src, cnt in cls.sources_stats(items, key=lambda i: i.ntags): # TODO ntags?
            x = T.div()
            x.add(cls.FTrait.tag_link(tag=src))
            x.add(f': {cnt}')
            res.add(x)
        # TODO dunno, it takes quite a bit of space... but cutting off those with 1 would be too annoying?
        res.add(T.div(T.b('User summary:')))
        for src, cnt in cls.sources_stats(items, key=lambda i: i.user):
            x = T.div()
            x.add(cls.FTrait.user_link(user=src))
            x.add(f': {cnt}')
            res.add(x)
        return res

CumulativeBase.reg(SpinboardCumulative)

class TentacleCumulative(ForTentacle, CumulativeBase):
    @classproperty
    def cumkey(cls):
        return lambda x: id(x)

    @classproperty
    def sortkey(cls):
        rev_when = invkey(lambda c: c.when)
        return lambda c: (-c.stars, rev_when(c))

    @cproperty
    def stars(self) -> int:
        # TODO vote for method??
        return vote(i.stars for i in self.items)

    def format(self):
        item = the(self.items)
        return self.FTrait.format_one(item)


CumulativeBase.reg(TentacleCumulative)

class ReachCumulative(ForReach, CumulativeBase):
    @cproperty
    def the(self): return the(self.items)

    @cproperty
    def ups(self):
        return self.the.ups

    @cproperty
    def downs(self):
        return self.the.downs

    @classproperty
    def cumkey(cls):
        return lambda x: id(x)

    @classproperty
    def sortkey(cls):
        invwhen  = invkey(lambda c: c.when)
        # invscore = invkey(lambda c: c.ups + c.downs)
        # TODO wtf, invkey didn't work..
        # return lambda c: (invscore(c), invwhen(c))
        return lambda c: (-(c.ups + c.downs), invwhen(c))

    def format(self):
        return self.FTrait.format_one(self.the)

    @classmethod
    def sources_summary(cls, items):
        # TODO FIXME clearly looks it could be generic..
        key = lambda i: i.subreddit
        for sub, cnt in cls.sources_stats(items, key=key):
            with T.div():
                cls.FTrait.user_link(sub)
                text(f': {cnt}')

CumulativeBase.reg(ReachCumulative)


class TwitterCumulative(ForTwitter, CumulativeBase):
    @cproperty
    def the(self):
        return the(self.items)

    @cproperty
    def interactions(self):
        th = the(self.items)
        return th.replies + th.retweets + th.likes

    @classproperty
    def cumkey(cls):
        return lambda x: id(x) # TODO FIXME ???

    @classproperty
    def sortkey(cls):
        invwhen  = invkey(when_key_tz_hack)
        return lambda c: (-c.interactions, invwhen(c))

    def format(self):
        return self.FTrait.format_one(self.the)

    @classmethod
    def sources_summary(cls, items):
        # TODO FIXME need adhoc thing?
        key = lambda i: i.user
        for sub, cnt in cls.sources_stats(items, key=key):
            with T.div():
                cls.FTrait.user_link(sub)
                text(f': {cnt}')


CumulativeBase.reg(TwitterCumulative)


class HackernewsCumulative(ForHackernews, CumulativeBase):
    @cproperty
    def the(self):
        return the(self.items)

    @classproperty
    def cumkey(cls):
        return lambda x: id(x) # TODO FIXME ???

    @cproperty
    def interactions(self):
        th = the(self.items)
        return th.points + th.comments

    @classproperty
    def sortkey(cls):
        invwhen  = invkey(lambda c: c.when)
        return lambda c: (-c.interactions, invwhen(c))

    def format(self):
        return self.FTrait.format_one(self.the)

    @classmethod
    def sources_summary(cls, items):
        # TODO eh. sort in reverse?
        key = lambda i: i.user
        for sub, cnt in cls.sources_stats(items, key=key):
            with T.div():
                cls.FTrait.user_link(sub)
                text(f': {cnt}')



CumulativeBase.reg(HackernewsCumulative)

# https://github.com/Knio/dominate/issues/63
# eh, looks like it's the intended way..
def raw_script(s):
    raw(f'<script>{s}</script>')


def render_summary(repo: Path, digest: Changes[Any], rendered: Path) -> Path:
    rtype = get_result_type(repo) # TODO ??
    # ODO just get trait for type??

    Cumulative = CumulativeBase.for_(rtype)

    NOW = datetime.now()
    name = repo.stem

    everything = list(flatten([ch for ch in digest.changes.values()]))

    before = len(everything)

    grouped = group_by_key(everything, key=Cumulative.cumkey)
    print(f'before: {before}, after: {len(grouped)}')

    cumulatives = list(map(Cumulative, grouped.values()))
    cumulatives = list(sorted(cumulatives, key=Cumulative.sortkey))

    doc = dominate.document(title=f'axol results for {name}, rendered at {fdate(NOW)}')
    with doc.head:
        T.style(STYLE)
        raw_script(JS)
    with doc:
        T.h3("This is axol search summary")
        T.div("You can use 'hide' function in JS (chrome debugger) to hide certain tags/subreddits/users")
        T.h4("Sources summary")
        # TODO wrap in div?
        with T.div():
            Cumulative.sources_summary(everything)
        for cc in cumulatives:
            T.div(cc.format(), cls='item')

    rendered.mkdir(exist_ok=True, parents=True)
    sf = rendered.joinpath(name + '.html')
    with sf.open('w') as fo:
        fo.write(str(doc))
    return sf


Item = Any # meh

def render_latest(repo: Path, digest, rendered: Path):
    logger.info('processing %s', repo)

    rtype = get_result_type(repo)
    Format = FormatTrait.for_(rtype)
    Ignore = IgnoreTrait.for_(rtype)

    import pytz
    NOW = datetime.now(tz=pytz.utc)

    name = repo.stem
    doc = dominate.document(title=f'axol results for {name}, rendered at {fdate(NOW)}')

    with doc.head:
        T.style(STYLE)
        raw_script(JS)

        T.link(rel='stylesheet', href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.2/codemirror.min.css")
        T.script(src='https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.48.2/codemirror.js') # TODO use min?

    citems: Iterator[Tuple[datetime, Item]] = chain.from_iterable(((d, x) for x in zz) for d, zz in digest.changes.items())
    # group according to link, so we can display already occuring items along with newer occurences
    items2: List[Sequence[Tuple[datetime, Item]]] = [grp for  _, grp in group_by_key(citems, key=lambda p: f'{p[1].link}').items()]
    # TODO sort within each group?

    def min_dt(group: Sequence[Tuple[datetime, Item]]) -> datetime:
        return min(g[0] for g in group)

    # TODO ok, this is def too many types here...
    items3: Mapping[datetime, List[Sequence[Tuple[datetime, Item]]]] = group_by_key(items2, key=min_dt)

    rss = True
    if rss:
        # pip3 install feedgen
        from feedgen.feed import FeedGenerator # type: ignore
        fg = FeedGenerator()
        # TODO memorize items?
        fg.title(name)
        fg.id('axol/' + name)
        first = True
        for d, items in sorted(items3.items()):
            litems = list(items)
            logger.info('%s %s: atom, dumping %d items', name, d, len(litems))
            if first:
                logger.info("SKIPPING first batch to prevent RSS bloat")
                first = False
                continue
            for zz in litems:
                fe = fg.add_entry()
                # TODO not sure about css?
                # TODO not sure which date should use? I gues crawling date makes more sense..
                _d, z = zz[0] # TODO meh!
                id_ = z.uid # TODO FIXME!!

                fe.id(id_)
                title = Format.title(zz) or '<no title>' # meh
                fe.title(title)
                fe.link(href=Format.link(zz))
                # TODO not sure if it's a reasonable date to use...
                fe.published(published=d)
                fe.author(author={'name': z.user}) # TODO maybe, concat users?

                ignored = Ignore.ignore_group(zz)
                if ignored is not None:
                    # TODO not sure if it highlights with read or something?
                    content = ignored
                else:
                    content = Format.format(zz)

                # eh, XML was complaining at some non-utf characters
                content = str(content)

                # https://stackoverflow.com/a/25920392/706389 make lxml happy...
                content = re.sub(u'[^\u0020-\uD7FF\u0009\u000A\u000D\uE000-\uFFFD\U00010000-\U0010FFFF]+', '', content)
                fe.content(content=content, type='CDATA')
                # fe.updated(updated=NOW)

                # TODO assemble a summary similar to HTML?
                # fe.summary()
        atomfeed = fg.atom_str(pretty=True)

        # eh, my feed reader (miniflux) can't handle it if it's 'cdata'
        # not sure which one is right
        # ugh, that didn't work because escaping desicion is based on CDATA attribute...
        atomfeed = atomfeed.replace(b'type="CDATA"', b'type="html"')
        # fe._FeedEntry__atom_content['type'] = 'html'

        atomdir = rendered / 'atom'
        atomdir.mkdir(parents=True, exist_ok=True)
        (atomdir / (name + '.xml')).write_bytes(atomfeed)

    with doc:
        with T.div(id='sidebar'):
            T.label('Blacklisted:', for_='blacklisted')
            T.div(id='blacklisted')
            T.textarea(id='blacklist-edit', rows=10)
            T.button('apply', id='blacklist-apply')


        odd = True
        for d, items in sorted(items3.items(), reverse=True):
            litems = list(items)
            odd = not odd
            logger.info('%s %s: dumping %d items', name, d, len(litems))
            with T.div(cls='day-changes'):
                with T.div():
                    T.b(fdate(d))
                    T.span(f'{len(litems)} items')

                with T.div(cls=f'day-changes-inner {"odd" if odd else "even"}'):
                    for i in items:
                        # TODO FIXME use getattr to specialise trait?
                        # TODO FIXME ignore should be at changes collecting stage?

                        ignored = Ignore.ignore_group(i)
                        if ignored is not None:
                            # TODO maybe let format result handle that... not sure
                            T.div(ignored, cls='item ignored')
                            # TODO log maybe?
                            # TODO eh. need to handle in cumulatives...
                        else:
                            fi = Format.format(i)
                            T.div(fi, cls='item')
        # fucking hell.. didn't manage to render content inside iframe no matter how I tried..
        # with T.iframe(id='blacklist', src=''):
        #     pass

    # TODO perhaps needs to be iterative...
    rf = rendered / (name + '.html')
    with rf.open('w') as fo:
        fo.write(str(doc))
    return rf


def setup_parser(p):
    from config import BASE_DIR, REPORTS_DIR
    p.add_argument('repos', nargs='*')
    p.add_argument('--with-summary', action='store_true')
    p.add_argument('--with-user-summary', action='store_true')
    p.add_argument('--last', type=int, default=None)
    # TODO rename output_dir?
    p.add_argument('--output-dir', type=Path, default=REPORTS_DIR)
    # TODO control via env variable instead? how to pass it to compose?
    p.add_argument('--serial', action='store_true', help='Do not use multithreading (useful for debugging)')


# TODO for starters, just send last few days digest..
def main():
    parser = argparse.ArgumentParser()
    setup_parser(parser)
    args = parser.parse_args()
    run(args)


def do_repo(repo, output_dir, last, summary: bool) -> Path:
    digest: Changes[Any] = get_digest(repo, last=last)
    RENDERED = output_dir / 'rendered'
    # TODO mm, maybe should return list of outputs..
    res = render_latest(repo, digest=digest, rendered=RENDERED)

    if summary:
        SUMMARY = output_dir/ 'summary'
        res = render_summary(repo, digest=digest, rendered=SUMMARY)
    return res


class Storage(NamedTuple):
    path: Path

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def source(self) -> str:
        return get_result_type(self.path)


def get_all_storages() -> Sequence[Storage]:
    return[Storage(path=x) for x in sorted(DATABASES.iterdir())] # TODO endswith sqlite?


def run(args):
    res: List[Storage]
    if len(args.repos) > 0:
        repos = [Storage(DATABASES / r) for r in args.repos]
    else:
        repos = get_all_storages()

    assert len(repos) > 0
    logger.info('will be processing %s', repos)

    storages = repos
    odir = args.output_dir

    odir.mkdir(exist_ok=True)

    if args.with_user_summary:
        user_summary(repos, output_dir=args.output_dir)

    # TODO would be cool to do some sort of parallel logging? 
    # maybe some sort of rolling log using the whole terminal screen?
    errors: List[str] = []

    if args.serial:
        # todo ugh, figure out how to do it easier... 
        from kython.koncurrent import DummyExecutor
        pool = DummyExecutor()
    else:
        pool = ProcessPoolExecutor()
    with pool:
        # TODO this is just pool map??
        futures = []
        for repo in repos:
            futures.append(pool.submit(do_repo, repo.path, output_dir=args.output_dir, last=args.last, summary=args.with_summary))
        for r, f in zip(repos, futures):
            try:
                f.result()
            except Exception as e:
                logger.error('while processing %s', r)
                logger.exception(e)
                err = f'while processing {r}: {e}'
                errors.append(err)

    # TODO put errors on index page?
    write_index(storages, odir)


    if len(errors) > 0:
        for e in errors:
            logger.error(e)
        sys.exit(1)


if __name__ == '__main__':
    main()
# TODO how to make it generic to incorporate github??


# basically a thing that knows how to fetch items with timestsamps
# and notify of new ones..

# TODO need to plot some nice dashboard..

def write_index(storages, output_dir: Path):
    now = datetime.now()
    doc = dominate.document(title=f'axol index for {[s.name for s in storages]}, rendered at {fdate(now)}')

    # TODO don't need this anymore?
    rss = True
    if rss:
        outlines = []
        for storage in storages:
            name = storage.name
            htmlUrl = 'https://whatever'
            url = f'https://unstable.beepb00p.xyz/atom/{name}.xml'
            outlines.append(f'<outline title="{name}" text="{name}" xmlUrl="{url}" htmlUrl="{htmlUrl}"></outline>')
        outliness = "\n".join(outlines)
        XML = f"""
<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
    <body>
        <outline text="All">
                {outliness}
        </outline>
    </body>
</opml>
        """
        (output_dir / 'rendered' / 'atom' / 'feeds.opml').write_text(XML)


    with doc.head:
        T.style(STYLE)

    with doc.body:
        with T.table():
            for storage in storages:
                with T.tr():
                    T.td(storage.name)
                    T.td(T.a('summary', href=f'summary/{storage.name}.html'))
                    T.td(T.a('history', href=f'rendered/{storage.name}.html'))
        T.div(T.b(T.a('pinboard users summary', href=f'pinboard_users.html')))
        T.div(T.b(T.a('reddit users summary'  , href=f'reddit_users.html')))
        T.div(T.b(T.a('github users summary'  , href=f'github_users.html')))
        T.div(T.b(T.a('twitter users summary' , href=f'twitter_users.html')))

    # TODO 'last updated'?
    (output_dir / 'index.html').write_text(str(doc))


def user_summary(storages, output_dir: Path):
    for src, st in group_by_key(storages, key=lambda s: s.source).items():
        rtype = the(get_result_type(x) for x in st)
        outf = output_dir / (For(src).name + '_users.html')
        user_summary_for(rtype=rtype, storages=st, output_path=outf)


def user_summary_for(rtype, storages, output_path: Path):
    ustats = {}
    def reg(user, query, stats):
        if user not in ustats:
            ustats[user] = {}
        ustats[user][query] = stats

    with ProcessPoolExecutor() as pp:
        digests = pp.map(get_digest, [s.path for s in storages])

    for s, digest in zip(storages, digests):
        everything = list(flatten([ch for ch in digest.changes.values()]))
        for user, items in group_by_key(everything, key=lambda x: x.user).items():
            reg(user, s.name, len(items))

    now = datetime.now()
    doc = dominate.document(title=f'axol tags summary for {[s.name for s in storages]}, rendered at {fdate(now)}')
    with doc.head:
        T.style(STYLE)
        raw_script(JS) # TODO necessary?

        # TODO FIXME can't inline due to some utf shit
        sortable_js = Path(__file__).absolute().parent / 'js' / 'sorttable.js'
        T.script(src=str(sortable_js))

    ft = FormatTrait.for_(rtype)
    with doc.body:
        with T.table(cls='sortable'):
            emitted_head = False
            for user, stats in sorted(ustats.items(), key=lambda x: (-len(x[1]), x)):
                if not emitted_head:
                    with T.thead():
                        T.td('user')
                        for q, _ in stats.items():
                            T.td(q)
                    emitted_head = True

                with T.tr():
                    T.td(ft.user_link(user))
                    for q, st in stats.items():
                        with T.td(sorttable_customkey=str(st)):
                            # TODO I guess unclear which tag to choose though.
                            T.a(q, href=f'summary/{q}.html') # TODO link to source in index? or on pinboard maybe
                            # TODO also project onto user's tags straight away
                            T.sup(str(st) if st < 5 else T.b(T.font(str(st), color='red'))) # TODO css

    output_path.write_text(str(doc))
    logger.info('Dumped user summary to %s', output_path)

