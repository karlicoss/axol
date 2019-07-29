from datetime import datetime
from typing import List, Dict, NamedTuple, Optional, Iterator
import logging


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



# TODO move this to scrapy_singlefile (and rename to 'adhoc'??)
# _items = []
#
# class AppendToList(object):
#     def process_item(self, item, spider):
#         _items.append(item)
#
# def scrapy_search(query: str):
#     assert len(_items) == 0
#
#     from scrapy.crawler import CrawlerProcess # type: ignore
#     from kython import import_from
#     scrape = import_from('/L/zzz_syncthing/tmp/TweetScraper', 'TweetScraper')
#     print(dir(scrape))
#     from TweetScraper.spiders.TweetCrawler import TweetScraper
#
#     process = CrawlerProcess({
#         'ITEM_PIPELINES': {__name__ + '.AppendToList': 100},
#         'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36',
#         'LOG_LEVEL': 'DEBUG',
#         'DUPEFILTER_DEBUG': True,
#     })
#     process.crawl(TweetScraper, query=query)
#     process.start() # blocking
#     # TODO FIXME inject some callback into reactor?
#     try:
#         return [i for i in _items]
#     finally:
#         _items.clear()


class TwitterSearch:
    def __init__(self) -> None:
        self.logger = get_logger()
        # TODO FIXME delay?
        # self.d

    def iter_search(self, query, limit=None) -> Iterator[Result]:
        from twitterscraper import query_tweets # type: ignore
        # TODO FIXME not sure if we can be iterative here..
        for i in sorted(query_tweets(query, limit=limit)):
            yield Result(
                uid =i.id,
                when=i.timestamp, # no tz, apparently local scraping tz?
                link=i.url,
                text=i.text,
                user=i.user, # TOOD not sure if need to keep user_id
                replies=i.replies,
                retweets=i.retweets,
                likes=i.likes,
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
