import json
from pathlib import Path
import time

from axol.common import Query, logger
from axol.crawl import RepoHandle, process_query


def test_repohandle(tmp_path):
    td = Path(tmp_path)
    rh = RepoHandle.create('test', path=td)
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

    testrange.clear(); testrange.extend([10, 11, 12])
    process_query(q=q, dry=False, path=td)

    # TODO eh?? FIXME duplication of things across queries?
    assert len(contents()) == 6
