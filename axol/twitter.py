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
    # TODO fixme not sure about title?..
    # pass



_items = []

class AppendToList(object):
    def process_item(self, item, spider):
        _items.append(item)

def scrapy_search(query: str):
    assert len(_items) == 0

    from scrapy.crawler import CrawlerProcess # type: ignore
    from kython import import_from
    scrape = import_from('/L/zzz_syncthing/tmp/TweetScraper', 'TweetScraper')
    print(dir(scrape))
    from TweetScraper.spiders.TweetCrawler import TweetScraper

    process = CrawlerProcess({
        'ITEM_PIPELINES': {__name__ + '.AppendToList': 100},
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36',
        'LOG_LEVEL': 'DEBUG',
        'DUPEFILTER_DEBUG': True,
    })
    process.crawl(TweetScraper, query=query)
    process.start() # blocking
    # TODO FIXME inject some callback into reactor?
    try:
        return [i for i in _items]
    finally:
        _items.clear()


class TwitterSearch:
    def __init__(self) -> None:
        self.logger = get_logger()
        # TODO FIXME delay?
        # self.d

    def iter_search(self, query, limit=None) -> Iterator[Result]:
        # TODO FIXME not sure if we can be iterative here..
        # TODO FIXME respect limit if we make it iterative?
        for i in scrapy_search(query=query):
            yield Result(
                uid =i['ID'],
                when=i['datetime'], # TODO FIXME # TO
                link=i['url'],
                text=i['text'],
                user=i['usernameTweet'], # TOOD not sure if need to keep user_id
                # TODO FIXME fav/rt stats?
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
    for r in ts.search('"quantified self"'):
        print(r)

# TODO set some limit?
# {'ID': '1146731105485250562',
#  'datetime': '2019-07-04 11:42:55',
#  'has_media': True,
#  'is_reply': False,
#  'is_retweet': False,
#  'medias': ['https://t.co/TV9SPFJUFO'],
#  'nbr_favorite': 3,
#  'nbr_reply': 2,
#  'nbr_retweet': 0,
#  'text': 'В общем, знайте, что есть только один канон Русалочки\n'
#          '\n'
#          ' Виктор Аргонов  Project — Сделать шаг (Ария сказочницы)  https:// '
#          'music.yandex.ru/album/3639147/ track/30168045 \xa0 …',
#  'url': '/kazdalevsky/status/1146731105485250562',
#  'user_id': '159019766',
#  'usernameTweet': 'kazdalevsky'}



if __name__ == '__main__':
    main()
