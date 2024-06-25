import json
from pathlib import Path
import time
from subprocess import check_output

from axol.common import Query, logger
from axol.crawl import process_query
from axol.storage import get_digest
from axol.database import DbWriter, DbReader
import axol.adhoc


def test_dbwriter(tmp_path):
    td = Path(tmp_path)
    dw = DbWriter(td / 'test.sqlite')
    jsons = [{'uid': str(i)} for i in range(10)]
    dw.commit(jsons, query='test')
    time.sleep(0.5)
    dw.commit(jsons, query='test')


testrange = list(range(15))

def get_testdata(q):
    from datetime import datetime, timedelta
    from spinboard import Result
    # TODO overlap some of them??
    dd = datetime(year=2000, month=1, day=4)
    spinboards = [Result(
        uid=str(i),
        when=dd + timedelta(hours=i),
        link='TODO',
        title=f'Title {i}',
        description=None,
        user='testuser',
        tags=['tag1', 'tag2'],
    ) for i in testrange]
    data = {
        'query1': spinboards[:10],
        'query2': spinboards[-10:],
    }
    return data[q]

class TestSearcher:
    def search_all(self, queries):
        for q in queries:
            yield from get_testdata(q)


class TestQ(Query):
    def __init__(self, *queries) -> None:
        self.queries = queries

    @property
    def searcher(self):
        return TestSearcher

    @property
    def sname(self):
        raise NotImplementedError

    @property
    def repo_name(self) -> str:
        return 'test_repo'


def count(db: Path) -> int:
    assert db.is_file(), db # precondition
    res = check_output([
        'sqlite3',
        db,
        'select count(distinct uid) from results',
    ]).decode('utf8').strip()
    return int(res)


def test_crawl(tmp_path):
    td = Path(tmp_path)

    trp = td / 'test_repo'
    db = trp.with_suffix('.sqlite')

    q = TestQ('query1', 'query2')
    process_query(q=q, dry=True, path=td)
    assert not db.exists() # dry run, shouldn't create anything
   

    # TODO eh, global trait is kind of meh?
    # maybe makes more sense to do lru cache and configuring

    process_query(q=q, dry=False, path=td)
    assert count(db) == 15

    # TODO meh, sleeps because of timestamping..
    time.sleep(1)
    testrange.clear(); testrange.extend([10, 11, 12, 17, 18])
    process_query(q=q, dry=False, path=td)

    time.sleep(1)
    process_query(q=q, dry=False, path=td)
    # this should be ignored in digest?

    assert count(db) == 17 # added 17 and 18

    # TODO split in other test

    digest = get_digest(db)
    assert [p[1] for p in sorted((k, len(v)) for k, v in digest.changes.items())] == [15, 2]


def test_adhoc(tmp_path):
    td = tmp_path

    # TODO eh, could render separately...
    # TODO just output htmls as it goes
    # axol adhoc [--summary] (--all  | --pinboard | --github | --reddit) 'query1' 'query2' 'query3'
    # TODO not sure if needs some sort of limit? and maybe lower timeout
    # TODO qname is temporary?
    # TODO not sure if should keep separate storages separate? Or maybe story query alongside?
    from .queries import GithubQ

    query = GithubQ('qmind', 'quantified mind')
    
    axol.adhoc.do_run(queries=[query], tdir=td)

    [db] = list(td.rglob('*.sqlite'))
    assert count(db) > 0
    # TODO html??

import pytest # type: ignore

def searchers_gen():
    from .queries import GithubQ, PinboardQ, TwitterQ, RedditQ, HackernewsQ
    yield from [GithubQ, PinboardQ, TwitterQ, RedditQ, HackernewsQ]

@pytest.mark.parametrize('searcher', searchers_gen())
def test_queries(tmp_path, searcher):
    tdir = tmp_path
    q = searcher('test', '"unlikely query"')
    process_query(q, dry=False, path=tdir)



def astext(html: Path) -> str:
    from subprocess import check_output
    return check_output(['html2text', str(html)]).decode('utf8')


# TODO fragile...
def test_all(tmp_path):
    tdir = Path(tmp_path)
    from config import RESULTS
    repo = RESULTS / 'pinboard_bret_victor.sqlite'
    digest = get_digest(repo)
    from .report import render_latest
    render_latest(repo, digest=digest, rendered=tdir)
    out = tdir / 'pinboard_bret_victor.html'

    ht = out.read_text()

    assert 'http://worrydream.com/MagicInk/' in ht
    assert 'http://enjalot.com/' in ht


    text = astext(out).splitlines()
    def tcontains(x):
        for line in text:
            if x in line:
                return True
        return False

    assert tcontains('09 Jul 2019 13:10')
    assert tcontains('07_Jul_2019_04:45 by barronwebster')
    assert tcontains('#computing #interaction #reading')


def test_digest():
    from config import RESULTS
    dd = get_digest(RESULTS / 'pinboard_bret_victor.sqlite')
    from itertools import chain
    everything = list(chain.from_iterable(v for _, v in dd.changes.items()))
    assert len(everything) == len({x.uid for x in everything})


def test_db_reader():
    from config import RESULTS
    from pathlib import Path
    hh = DbReader(Path(RESULTS / 'pinboard_arbtt.sqlite'))
    assert len(list(hh.iter_versions())) > 5
