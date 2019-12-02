import json
from pathlib import Path
import time

from axol.common import Query, logger
from axol.crawl import process_query
from axol.storage import RepoWriteHandle, get_digest
import axol.adhoc


def test_repohandle(tmp_path):
    td = Path(tmp_path)
    rh = RepoWriteHandle.create('test', base=td)
    jsons = [{i: str(i) for i in range(10)}]
    rh.commit(jsons)
    time.sleep(0.5)
    rh.commit(jsons)
    # TODO then run storage and check digests?



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


def test_crawl(tmp_path):
    td = Path(tmp_path)

    trp = td / 'test_repo'
    q = TestQ('query1', 'query2')
    process_query(q=q, dry=True, path=td)
    assert not trp.exists()

    # TODO eh, global trait is kind of meh?
    # maybe makes more sense to do lru cache and configuring
    def contents():
        return json.loads((trp / 'content.json').read_text())

    process_query(q=q, dry=False, path=td)
    assert len(contents()) == 20

    # TODO FIXME because of git time. ugh
    time.sleep(2)
    testrange.clear(); testrange.extend([10, 11, 12, 17, 18])
    process_query(q=q, dry=False, path=td)

    time.sleep(2)
    process_query(q=q, dry=False, path=td)
    # this should be ignored in digest?

    # TODO eh?? FIXME duplication of things across queries?
    assert len(contents()) == 10

    # TODO split in other test

    digest = get_digest(trp)
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

    [js] = list(td.rglob('*.json'))
    assert len(json.loads(js.read_text())) > 0
    # TODO html??

import pytest

def searchers_gen():
    from .queries import GithubQ, PinboardQ, TwitterQ, RedditQ
    yield from [GithubQ, PinboardQ, TwitterQ, RedditQ]

@pytest.mark.parametrize('searcher', searchers_gen())
def test_queries(tmp_path, searcher):
    tdir = tmp_path
    q = searcher('test', '"unlikely query"')
    process_query(q, dry=False, path=tdir)




