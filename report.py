#!/usr/bin/env python3
import argparse
from datetime import datetime
from json import loads
from itertools import islice
from subprocess import check_call, check_output
from typing import List, Tuple, Dict, Type, Union, Any
import logging
import sys
from pathlib import Path
from os.path import basename, join
from collections import Counter

from common import get_logger, setup_paths, classproperty
setup_paths()
from config import OUTPUTS
from jsonify import from_json

import dominate # type: ignore
from dominate import tags as T # type: ignore

from kython import flatten
from kython.logging import setup_logzero


class RepoHandle:
    def __init__(self, repo: str):
        self.repo = repo

    def check_output(self, *args):
        return check_output([
            'git', f'--git-dir={self.repo}/.git', *args
        ])

    def get_revisions(self) -> List[Tuple[str, datetime]]:
        ss = list(reversed(self.check_output(
            'log',
            '--pretty=format:%h %ad',
            '--no-patch',
        ).decode('utf8').splitlines()))
        def pdate(l):
            ds = ' '.join(l.split()[1:])
            return datetime.strptime(ds, '%a %b %d %H:%M:%S %Y %z')
        return [(l.split()[0], pdate(l)) for l in ss]

    def get_content(self, rev: str) -> str:
        return self.check_output(
            'show',
            rev + ':content.json',
        ).decode('utf8')

    def get_all_versions(self):
        revs = self.get_revisions()
        jsons = []
        for rev, dd in revs:
            cc = self.get_content(rev)
            if len(cc.strip()) == 0:
                j = {}
            else:
                j = loads(cc)
            jsons.append((rev, dd, j))
        return jsons

def diffference(before, after):
    db = {x.uid: x for x in before}
    da = {x.uid: x for x in after}
    removed = []
    added = []
    for x in {*db.keys(), *da.keys()}:
        if x in db and x not in da:
            removed.append(db[x])
        elif x not in db and x in da:
            added.append(da[x])
        elif x in db and x in da:
            pass # TODO compare??
        else:
            raise AssertionError
    return removed, added

class Collector:
    def __init__(self):
        self.items: Dict[str, Any] = {}

    def register(self, batch):
        added = []
        for i in batch:
            if i.uid in self.items:
                pass # TODO FIXME compare? if description or tags changed, report it?
            else:
                added.append(i)
                self.items[i.uid] = i
        return added

# TODO need some sort of starting_from??
# TODO I guess just use datetime?

from trait import AbsTrait, pull

Htmlish = Union[str, T.dom_tag]

# TODO use Genetic[T]??

# TODO hmm. maybe calling base class method pulls automatically??
class FormatTrait(AbsTrait):
    _impls = {}

    # TODO go through registered classes and dispatch
    # TODO not sure about extras...
    # TODO first arg for format is this??
    @classmethod
    def format(trait, obj, *args, **kwargs) -> Htmlish:
        raise NotImplementedError


    # TODO crap. does it have to be a separate trait??
    # @classmethod
    # def format(trait, cobj)
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

# TODO move target separately?
class ForSpinboard:
    @classproperty
    def Target(cls):
        from spinboard import Result # type: ignore
        return Result

class ForReach:
    @classproperty
    def Target(cls):
        from reach import Result # type: ignore
        return Result

class ForTentacle:
    @classproperty
    def Target(cls):
        from tentacle import Result # type: ignore
        return Result

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
        for t in obj.tags:
            res.add(T.a(t, href=SpinboardFormat.plink(user=obj.user, tag=t)))
        res.add(T.br())
        res.add(T.a(f'{fdate(obj.when)} by {obj.user}', href=obj.blink, cls='permalink'))
        # TODO userstats
        return res
# TODO better name for reg
FormatTrait.reg(SpinboardFormat)

class ReachFormat(ForReach, FormatTrait):
    @classmethod
    def format(trait, obj, *args, **kwargs) -> Htmlish:
        res = T.div(cls='reddit')
        res.add(T.a(obj.title, href=obj.link))
        res.add(T.br())
        if not isempty(obj.description):
            res.add(obj.description)
            res.add(T.br())
        # TODO user and subreddit and misc?
        res.add(T.a(f'{obj.when.strftime("%Y-%m-%d %H:%M")} by {obj.user}', cls='permalink')) # TODO link..
        return res
FormatTrait.reg(ReachFormat)

class TentacleTrait(ForTentacle, FormatTrait):
    # TODO mm. maybe permalink is a part of trait?
    @classmethod
    def format(trait, obj, *args, **kwargs) -> Htmlish:
        res = T.div(cls='github')
        res.add(T.span(obj.title))
        res.add(T.span(f'{obj.stars}★'))
        res.add(T.br())
        if not isempty(obj.description):
            res.add(obj.description)
            res.add(T.br())
        res.add(T.a(f'{obj.when.strftime("%Y-%m-%d %H:%M")} by {obj.user}', href=obj.link, cls='permalink'))
        return res
        # TODO indicate how often is user showing up?
FormatTrait.reg(TentacleTrait)

# TODO maybe, move to jsonify?..
def get_result_type(repo: str) -> Type:
    name = basename(repo)
    if name.startswith('reddit'):
        from reach import Result # type: ignore
        return Result
    elif name.startswith('github'):
        from tentacle import Result # type: ignore
        return Result
    else:
        from spinboard import Result # type: ignore
        return Result


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

class Changes:
    def __init__(self) -> None:
        self.changes: Dict[datetime, List[str]] = {}
    # method to format everything?

    def add(self, rev: datetime, items):
        self.changes[rev] = items

    def __len__(self):
        return sum(len(x) for x in self.changes.values())

# TODO html mode??
def get_digest(repo: str, count=None) -> Changes:
    rtype = get_result_type(repo)

    count = None
    # if count is None:
    #     count = 100 # TODO fixme! maybe append if count is trimmed?
        # TODO maybe, instead of email just check the html occasionnally? email takes quite a bit of time

    rh = RepoHandle(repo)
    jsons = rh.get_all_versions()
    # ustats = get_user_stats(jsons, rtype=rtype)
    ustats = None

    # TODO shit. should have stored metadata in repository?... for now guess from filename..

    cc = Collector()
    changes = Changes()
    # TODO maybe collector can figure it out by itself? basically track when the item was 'first se
    for jj in jsons:
        rev, dd, j = jj
        items = list(map(lambda x: from_json(rtype, x), j))
        added = cc.register(items)
        #print(f'revision {rev}: total {len(cc.items)}')
        #print(f'added {len(added)}')
        # if first:
        if len(added) == 0:
            continue
        formatted = list(sorted(added, key=lambda e: e.when, reverse=True))
        # not sure if should keep revision here at all..
        changes.add(dd, formatted)
        # TODO link to user
        # TODO user weight?? count is fine I suppose...
        # TODO added date
#        if len(added) > 0:
#            for r in sorted(added, key=lambda r: r.uid):
#                # TODO link to bookmark
#                # TODO actually chould even generate html here...
#                # TODO highlight interesting users
#                # TODO how to track which ones were already notified??
#                # TODO I guess keep latest revision in a state??

    return changes

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

.permalink {
    color: gray;
}

.day-changes-inner {
    margin-left: 15px;
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
    _impls = {}

    def __init__(self, items: List) -> None:
        self.FTrait = FormatTrait.for_(self.Target)
        self.items = items

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
        tt = {x for x in sum((i.tags for i in self.items), [])}
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
            res.add(T.a(t, href=self.FTrait.plink(tag=t)))
        res.add(T.br())
        pl = T.div(f'{fdate(self.when)} by', cls='permalink')
        fusers = [T.a(u, href=self.FTrait.plink(user=u)) for u in self.users]
        for f in fusers:
            pl.add(T.span(f))
        res.add(pl)
        return res
CumulativeBase.reg(SpinboardCumulative)

class TentacleCumulative(ForTentacle, CumulativeBase):
    @classproperty
    def cumkey(cls):
        return lambda x: id(x)

    @classproperty
    def sortkey(cls):
        return lambda c: c.stars

    @property
    @lru_cache()
    def stars(self) -> int:
        # TODO vote for method??
        return vote(i.stars for i in self.items)

    def format(self):
        assert len(self.items) == 1
        return self.FTrait.format(self.items[0])
CumulativeBase.reg(TentacleCumulative)


def render_summary(repo, rendered: Path = None):
    rtype = get_result_type(repo) # TODO ??
    # ODO just get trait for type??

    Cumulative = CumulativeBase.for_(rtype)

    digest = get_digest(repo)
    NOW = datetime.now()
    name = basename(repo)

    everything = flatten([ch for ch in digest.changes.values()])

    before = len(everything)


    # TODO group key is unique.. should I make it object id??
    grouped = group_by_key(everything, key=Cumulative.cumkey)
    print(f'before: {before}, after: {len(grouped)}')

    # TODO sort key for summary??
    cumulatives = list(map(Cumulative, grouped.values()))
    cumulatives = list(sorted(cumulatives, key=Cumulative.sortkey))

    doc = dominate.document(title=f'axol results for {name}, rendered at {fdate(NOW)}')
    with doc.head:
        T.style(STYLE)
    with doc:
        for cc in cumulatives:
            doc.add(T.div(cc.format(), cls='item'))

    with rendered.joinpath(name + '.html').open('w') as fo:
        fo.write(str(doc))

def handle_one(repo: str, html=False, email=True, rendered: Path = None):
    digest = get_digest(repo)
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

        name = basename(repo)
        doc = dominate.document(title=f'axol results for {name}, rendered at {fdate(NOW)}')

        with doc.head:
            T.style(STYLE)

        # TODO email that as well?
        with doc:
            for d, items in sorted(digest.changes.items(), reverse=True):
                with T.div(cls='day-changes') as dc:
                    dc.add(T.div(T.b(fdate(d))))
                    # TODO tab?
                    with T.div(cls='day-changes-inner') as dci:
                        for i in items:
                            fi = format_result(i)
                            # TODO append raw?
                            dci.add(T.div(fi, cls='item'))
            # with div(id='header').add(ol()):
            #     for i in ['home', 'about', 'contact']:
            #         li(a(i.title(), href='/%s.html' % i))

            # with div():
            #     attr(cls='body')
            #     p('Lorem ipsum..')

        # print(doc)
        with rendered.joinpath(name + '.html').open('w') as fo:
            fo.write(str(doc))



# TODO for starters, just send last few days digest..
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('repo', nargs='?')
    parser.add_argument('--summary', action='store_true')
    parser.add_argument('--no-email', action='store_false', dest='email')
    parser.add_argument('--no-html', action='store_false', dest='html')
    args = parser.parse_args()

    logger = get_logger()
    setup_logzero(logger, level=logging.DEBUG)

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
    for repo in repos:
        try:
            logger.info("Processing %s", repo)
            if args.summary:
                SUMMARY = Path(__file__).parent.joinpath('summary').resolve()
                render_summary(str(repo), rendered=SUMMARY)
            else:
                RENDERED = Path(__file__).parent.joinpath('rendered').resolve()
                handle_one(str(repo), html=args.html, email=args.email, rendered=RENDERED)
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
