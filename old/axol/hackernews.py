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

        ## ugh. hasn't been updated for a while
        from hn.utils import AVAILABLE_DATE_FORMATS
        fff = '%Y-%m-%dT%H:%M:%SZ'
        if fff not in AVAILABLE_DATE_FORMATS:
            AVAILABLE_DATE_FORMATS.append(fff)
        ##

        results = search_by_date(query)
        # By default, all the different "post types" will be included: stories, comments, polls, etc.

        for r in results:
            crs = r['created_at']
            crs = crs.replace('Z', '+00:00')  # TODO should be working without this after python 3.10
            dt = datetime.fromisoformat(crs)
            p = r.get('points')
            p = -1 if p is None else p
            st = r.get('story_text')
            ct = r.get('comment_text')  # can be missing
            assert not (st is not None and ct is not None), r
            text = st or ct or ''
            nc = r.get('num_comments')
            nc = -1 if nc is None else nc

            url = r.get('story_url') or r.get('url')
            if url is None:
                story_id = r['story_id']
                url = r'https://news.ycombinator.com/item?id={story_id}'  # meh, but sometimes missing

            title = r.get('story_title') or r.get('title')
            assert title is not None, r

            yield Result(
                uid=r['objectID'],
                when=dt,
                user=r['author'],
                url=url,
                title=title,
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
