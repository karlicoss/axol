import scrapy # type: ignore
from scrapy.crawler import CrawlerProcess # type: ignore


from kython import import_from

# scrape = import_from('/L/zzz_syncthing/tmp/TweetScraper', 'TweetScraper')
from TweetScraper.spiders.TweetCrawler import TweetScraper

from scrapy.settings import Settings

items = []

# pipeline to fill the items list
class ItemCollectorPipeline(object):
    def __init__(self):
        self.ids_seen = set()
        print("INSTANTIATING!")

    def process_item(self, item, spider):
        items.append(item)

def main():
    process = CrawlerProcess({
        'ITEM_PIPELINES': { '__main__.ItemCollectorPipeline': 100 },  # TODO what does the number mean?
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36',
        'LOG_LEVEL': 'DEBUG',
        'DUPEFILTER_DEBUG': True,
    })
    process.crawl(TweetScraper, query='"виктор аргонов"')
    process.start() # blocking
    for i in items:
        import ipdb; ipdb.set_trace() 
        print(i)

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
