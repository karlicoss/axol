#!/usr/bin/env python3
import argparse
from datetime import datetime
from itertools import islice
from subprocess import check_call, check_output
from typing import List, Tuple, Dict, Type, Union, Any, Iterator, Optional
import logging
import sys
from pathlib import Path
from collections import Counter

from axol.common import setup_paths, classproperty, logger
from config import OUTPUTS, ignored_reddit
from axol.storage import RepoHandle, get_digest, get_result_type
from axol.traits import ignore_result
from axol.traits import ForSpinboard, ForTentacle, ForReach
from axol.trait import AbsTrait, pull

import dominate # type: ignore
from dominate import tags as T # type: ignore
from dominate.util import raw # type: ignore

from kython import flatten



# TODO need some sort of starting_from??
# TODO I guess just use datetime?


Htmlish = Union[str, T.dom_tag]

# TODO use Genetic[T]??

# TODO hmm. maybe calling base class method pulls automatically??
class FormatTrait(AbsTrait):
    @classmethod
    def format(trait, obj, *args, **kwargs) -> Htmlish:
        raise NotImplementedError
format_result = pull(FormatTrait.format)


def isempty(s) -> bool:
    if s is None:
        return True
    if len(s.strip()) == 0:
        return True
    return False

# def fdate(d: datetime) -> str:
#     return d.strftime("%Y-%m-%d %H:%M")

def fdate(d: datetime) -> str:
    return d.strftime('%a %d %b %Y %H:%M')



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
        return T.a(tag, href=ll, cls='tag')

    @classmethod
    def user_link(cls, user: str):
        ll = cls.plink(user=user)
        return T.a(user, href=ll, cls='user')

    # TODO default formatter?
    # TODO Self ?? maybe it should be metaclass or something?
    @classmethod
    def format(trait, obj, *args, **kwargs) -> Htmlish:
        # TODO would be nice to have spinboard imported here for type checking..
        res = T.div(cls='pinboard')
        res.add(T.a(obj.title, href=obj.link))
        res.add(T.br())
        if not isempty(obj.description):
            res.add(obj.description)
            res.add(T.br())
        res.add('tags: ')
        for t in obj.ntags:
            res.add(trait.tag_link(tag=t, user=obj.user))
        res.add(T.br())
        res.add(T.a(f'{fdate(obj.when)}', href=obj.blink, cls='permalink'))
        res.add(' by')
        res.add(trait.user_link(user=obj.user))
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
    def format(trait, obj, *args, **kwargs) -> Htmlish:
        res = T.div(cls='reddit')
        ll = reddit(obj.link)

        ud = f'{obj.ups}⇅{obj.downs}'
        res.add(T.a(obj.title, href=ll))
        res.add(T.span(ud))
        res.add(T.br())

        if not isempty(obj.description):
            res.add(obj.description)
            res.add(T.br())
        res.add(T.div(trait.subreddit_link(obj.subreddit)))
        user_link = reddit('/u/' + obj.user)
        res.add(T.a(f'{obj.when.strftime("%Y-%m-%d %H:%M")}', href=ll, cls='permalink')); res.add(' by '); res.add(T.a(obj.user, href=user_link, cls='user'))
        return res

class TentacleTrait(ForTentacle, FormatTrait):
    # TODO mm. maybe permalink is a part of trait?
    @classmethod
    def format(trait, obj, *args, **kwargs) -> Htmlish:
        res = T.div(cls='github')
        res.add(T.a(obj.title, href=obj.link))
        res.add(T.span(f'{obj.stars}★'))
        res.add(T.br())
        if not isempty(obj.description):
            res.add(obj.description)
            res.add(T.br())
        res.add(T.a(f'{obj.when.strftime("%Y-%m-%d %H:%M")} by {obj.user}', href=obj.link, cls='permalink'))
        return res
        # TODO indicate how often is user showing up?

FormatTrait.reg(ReachFormat, SpinboardFormat, TentacleTrait)


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

STYLE = """

.item {
    margin-top:    10px;
    margin-bottom: 10px;
}

.item.ignored {
    color: gray;
    margin-top:    1px;
    margin-bottom: 1px;
}

.permalink {
    color: gray;
}

.day-changes-inner {
    margin-left: 15px;
}

.user {
    color: #035E7B;
}

.tag, .subreddit {
    color: darkgreen;
    /* color: #97130F; */
}

a:link {
  text-decoration: none;
}

a:visited {
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

a:active {
  text-decoration: underline;
}
"""

JS = """
function hide(thing) {
// TODO ugh, doesn't look like $x works in FF
    const items = $x(`.//div[@class='item' and .//a[text()='${thing}']]`);
    console.log(`hiding ${items.length} items`);
    items.forEach(el => { el.hidden = true; });
}
"""

from kython import group_by_key
from kython.url import normalise
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


class CumulativeBase(AbsTrait):
    def __init__(self, items: List) -> None:
        self.items = items

    @classproperty
    def FTrait(cls):
        return FormatTrait.for_(cls.Target)

    # TODO mabye cached_property?
    @property # type: ignore
    @lru_cache()
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
        # TODO also display total count??
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
        for src, cnt in cls.sources_stats(items, key=lambda i: i.ntags):
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
        return lambda c: (c.stars, rev_when(c))

    @property
    @lru_cache()
    def stars(self) -> int:
        # TODO vote for method??
        return vote(i.stars for i in self.items)

    def format(self):
        assert len(self.items) == 1
        return self.FTrait.format(self.items[0])


CumulativeBase.reg(TentacleCumulative)

class ReachCumulative(ForReach, CumulativeBase):
    @property
    @lru_cache()
    def the(self):
        assert len(self.items) == 1
        return self.items[0]

    @property
    @lru_cache()
    def ups(self):
        return self.the.ups

    @property
    @lru_cache()
    def downs(self):
        return self.the.downs

    @classproperty
    def cumkey(cls):
        return lambda x: id(x)

    @classproperty
    def sortkey(cls):
        invwhen = invkey(lambda c: c.when)
        return lambda c: (c.ups + c.downs, invwhen(c))

    def format(self):
        return self.FTrait.format(self.the)

    @classmethod
    def sources_summary(cls, items):
        res = T.div()
        for sub, cnt in cls.sources_stats(items, key=lambda i: i.subreddit):
            x = T.div()
            x.add(cls.FTrait.subreddit_link(sub))
            x.add(f': {cnt}')
            res.add(x)
        return res

CumulativeBase.reg(ReachCumulative)


# https://github.com/Knio/dominate/issues/63
# eh, looks like it's the intended way..
def raw_script(s):
    raw(f'<script>{s}</script>')


def render_summary(repo, rendered: Path, last=None):
    rtype = get_result_type(repo) # TODO ??
    # ODO just get trait for type??

    Cumulative = CumulativeBase.for_(rtype)

    digest = get_digest(repo, last=last)
    NOW = datetime.now()
    name = repo.name

    everything = flatten([ch for ch in digest.changes.values()])

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
        Cumulative.sources_summary(everything)
        for cc in cumulatives:
            T.div(cc.format(), cls='item')

    with rendered.joinpath(name + '.html').open('w') as fo:
        fo.write(str(doc))

def handle_one(repo: Path, rendered: Path, html=False, email=True, last=None):
    logger.info('processing %s', repo)


    digest = get_digest(repo, last=last)
    if email:
        raise RuntimeError('email is currenlty broken')
        # res = send(
        #     subject=basename(repo),
        #     body=digest,
        #     html=html,
        # )
        # res.raise_for_status()
    else:
        NOW = datetime.now()

        name = repo.name
        doc = dominate.document(title=f'axol results for {name}, rendered at {fdate(NOW)}')

        with doc.head:
            T.style(STYLE)

        # TODO email that as well?
        with doc:
            for d, items in sorted(digest.changes.items(), reverse=True):
                logger.debug('dumping %d items for %s', len(items), d)
                with T.div(cls='day-changes') as dc:
                    dc.add(T.div(T.b(fdate(d))))
                    # TODO tab?
                    with T.div(cls='day-changes-inner') as dci:
                        for i in items:
                            ignored = ignore_result(i)
                            if ignored is not None:
                                # TODO maybe let format result handle that... not sure
                                dci.add(T.div(ignored, cls='item ignored'))
                                # TODO eh. need to handle in cumulatives...
                            else:
                                fi = format_result(i)
                                # TODO append raw?
                                dci.add(T.div(fi, cls='item'))

        with rendered.joinpath(name + '.html').open('w') as fo:
            fo.write(str(doc))


def setup_parser(parser):
    BASE_DIR = Path(__file__).absolute().parent
    parser.add_argument('repo', nargs='?')
    parser.add_argument('--summary', action='store_true')
    parser.add_argument('--last', type=int, default=None)
    parser.add_argument('--no-email', action='store_false', dest='email')
    parser.add_argument('--no-html', action='store_false', dest='html')
    parser.add_argument('--output-dir', type=Path, default=BASE_DIR)


# TODO for starters, just send last few days digest..
def main():
    parser = argparse.ArgumentParser()
    setup_parser(parser)
    args = parser.parse_args()
    run(args)

def run(args):
    # parser.add_argument('--from', default=None)
    # parser.add_argument('--to', default=None)
    # froms = getattr(args, 'from')
    # TODO utc timestamp??
    # tos = args.to
    repos: List[Path] = []
    if args.repo is not None:
        repos = [OUTPUTS.joinpath(args.repo)]
    else:
        repos = [x for x in OUTPUTS.iterdir() if x.is_dir()]
    ok = True
    output_dir = args.output_dir
    for repo in repos:
        logger.info("processing %s", repo)
        try:
            if args.summary:
                SUMMARY = output_dir/ 'summary'
                render_summary(str(repo), rendered=SUMMARY, last=args.last)
            else:
                RENDERED = output_dir / 'rendered'
                handle_one(repo, html=args.html, email=args.email, rendered=RENDERED, last=args.last) # TODO handle last=thing uniformly..
        except Exception as e:
            logger.exception(e)
            ok = False

    if not ok:
        sys.exit(1)




if __name__ == '__main__':
    main()
# TODO how to make it generic to incorporate github??


# basically a thing that knows how to fetch items with timestsamps
# and notify of new ones..

# TODO need to plot some nice dashboard..

def astext(html: Path) -> str:
    from subprocess import check_output
    return check_output(['html2text', str(html)]).decode('utf8')


def test_all(tmp_path):
    tdir = Path(tmp_path)
    rr = OUTPUTS / 'bret_victor'
    handle_one(rr, html=True, email=False, rendered=tdir)
    out = tdir / 'bret_victor.html'

    ht = out.read_text()

    assert 'http://worrydream.com/MagicInk/' in ht
    assert 'http://enjalot.com/' in ht


    text = astext(out).splitlines()
    def tcontains(x):
        for line in text:
            if x in line:
                return True
        return False

    assert tcontains('Tue 18 Jun 2019 13:10')
    assert tcontains('Fri_14_Jun_2019_14:33 by pmf')
    assert tcontains('tags: bret_victor javascript mar12 visualization')


