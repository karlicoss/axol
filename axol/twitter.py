from datetime import datetime
import json
from pathlib import Path
import logging
from typing import List, NamedTuple, Iterable


def get_logger():
    return logging.getLogger('twisearch')


class Result(NamedTuple):
    uid: str
    when: datetime
    link: str
    text: str
    user: str
    replies: int
    retweets: int
    likes: int

    # TODO fixme not sure about title?..
    @property
    def title(self) -> str:
        return self.link


class TwitterSearch:
    def __init__(self) -> None:
        self.logger = get_logger()

    def iter_search(self, query, limit=None) -> Iterable[Result]:
        import twint # type: ignore

        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td:
            tdir = Path(td)
            tfile = tdir / 'results.json'
            c = twint.Config()
            c.Search = query
            c.Hide_output = True
            c.Store_json = True
            c.Output = str(tfile)
            twint.run.Search(c)
            # TODO limit, perhaps?

            # TODO how should they be sorted?
            # TODO actually iterative version would be nice..

            for t in map(json.loads, tfile.read_text().splitlines()):
                yield Result(
                    uid=str(t['id']),
                    when=datetime.fromtimestamp(t['created_at'] / 1000), # todo not sure what's the tz... but the payload also has timezone info?
                    link    =t['link'], # TODO generate from id and user?
                    text    =t['tweet'],
                    user    =t['username'],
                    replies =t['replies_count'],
                    retweets=t['retweets_count'],
                    likes   =t['likes_count'],
                )

    def search(self, query: str, limit=None) -> List[Result]:
        # TODO FIXME do I need to sort anything?
        return list(self.iter_search(query=query, limit=limit))

    # TODO FIXME search_all gonna look very similar?
    def search_all(self, queries: List[str], limit=None) -> List[Result]:
        assert len(queries) == 1 # TODO FIXME
        return self.search(query=queries[0], limit=limit)


def main():
    ts = TwitterSearch()
    for r in ts.search('"виктор аргонов"', limit=10):
        print(r)


if __name__ == '__main__':
    main()
