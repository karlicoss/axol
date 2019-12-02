from datetime import datetime
from typing import List, Dict, NamedTuple, Optional, Iterator
import logging


def get_logger():
    return logging.getLogger('hnsearch')


# {'created_at': '2019-11-06T20:39:38.000Z', 'title': 'Quantified Self', 'url': 'https://github.com/woop/awesome-quantified-self/blob/master/README.MD', 'author': 'dmvinson', 'points': 3, 'story_text': None, 'comment_text': None, 'num_comments': 0, 'story_id': None, 'story_title': None, 'story_url': None, 'parent_id': None, 'created_at_i': 1573072778, '_tags': ['story', 'author_dmvinson', 'story_21466974'], 'objectID': '21466974', '_highlightResult': {'title': {'value': '<em>Quantified Self</em>', 'matchLevel': 'full', 'fullyHighlighted': True, 'matchedWords': ['quantified', 'self']}, 'url': {'value': 'https://github.com/woop/awesome<em>-quantified-self</em>/blob/master/README.MD', 'matchLevel': 'full', 'fullyHighlighted': False, 'matchedWords': ['quantified', 'self']}, 'author': {'value': 'dmvinson', 'matchLevel': 'none', 'matchedWords': []}}}
# TODO parent_id??
class Result(NamedTuple):
    uid: str
    when: datetime
    user: str
    url: str
    title: str
    text: str

    points: int
    comments: int

    @property
    def link(self) -> str:
        # TODO permalink??
        return f'https://news.ycombinator.com/item?id={self.uid}'

class HackernewsSearch:
    def __init__(self) -> None:
        self.logger = get_logger()

    # TODO FIXME lots of code duplication with twitter
    def iter_search(self, query: str, limit=None) -> Iterator[Result]:
        from hn import search_by_date # pip3 install python-hn

        results = search_by_date(query)
        # By default, all the different "post types" will be included: stories, comments, polls, etc.

        for r in results:
            crs = r['created_at']
            dt = datetime.strptime(crs, '%Y-%m-%dT%H:%M:%S.%f%z')
            p = r['points']
            p = -1 if p is None else p
            st = r['story_text']
            ct = r['comment_text']
            assert not (st is not None and ct is not None)
            text = st or ct or ''
            nc = r['num_comments']
            nc = -1 if nc is None else nc

            yield Result(
                uid=r['objectID'],
                when=dt,
                user=r['author'],
                url=r['url'],
                title=r['title'],
                text=text,
                points=p,
                comments=nc,
            )

    def search(self, query: str, limit=None) -> List[Result]:
        # TODO FIXME do I need to sort anything?
        return list(self.iter_search(query=query, limit=limit))

    # TODO FIXME search_all gonna look very similar?
    def search_all(self, queries: List[str], limit=None) -> List[Result]:
        assert len(queries) == 1 # TODO FIXME
        return self.search(query=queries[0], limit=limit)
