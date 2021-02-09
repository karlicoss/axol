# Twitter brakes scrapers all the time...
# twint is pretty broken at the moment too
#
# * this doesn't work: pip3 install --user 'git+https://github.com/bisguzar/twitter-scraper.git'
#   from twitter_scraper import get_tweets
#   - couldn't search in russian:
#     UnicodeEncodeError: 'latin-1' codec can't encode characters in position 21-26: ordinal not in range(256
#   - and apart from that, search doesn't work anyway...
#     https://github.com/bisguzar/twitter-scraper/issues/168


from datetime import datetime
import json
from pathlib import Path
import re
import logging
from typing import List, NamedTuple, Iterable


from axol.core.klogging import LazyLogger

logger = LazyLogger('axol.twitter')

# sorry I don't know these languages
# FIXME make configurable... start with global and maybe later support per query
IGNORE_LANGUAGES = {
    'ja',
    'fr',
    'in',
    'it',
    'pt',
    'es',
}
# https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes

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


from contextlib import contextmanager
@contextmanager
def twint_debug_logging():
    # shit. twint uses logging module methods (so everything ends up in a root logger..)
    # os.environ['TWINT_DEBUG'] = 'debug' # in addition this writes to a file and you can't override this
    # TODO ugh. twint logger is very spammy, I'm not even sure what to filter...
    lvl = logging.DEBUG
    logger = logging.getLogger()
    orig_lvl = logger.level
    try:
        logger.setLevel(lvl)
        formatter = logging.Formatter('%(levelname)s:%(asctime)s:%(name)s:%(message)s')
        handler = logging.StreamHandler()
        handler.setLevel(lvl)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        yield
    finally:
        logger.setLevel(orig_lvl)
        logger.removeHandler(handler)


class TwitterSearch:
    def iter_search(self, query, limit=None) -> Iterable[Result]:
        # TODO for cli, should allow individual params, e.g. --limit. maybe via click?
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as td: # , twint_debug_logging():
            import twint # type: ignore
            tdir = Path(td)
            tfile = tdir / 'results.json'
            c = twint.Config()
            c.Search = query
            c.Hide_output = True
            c.Store_json = True
            c.Output = str(tfile)
            # c.Limit = 1000 # useful for debugging
            twint.run.Search(c)
            # TODO limit, perhaps?

            # TODO how should they be sorted?
            # TODO actually iterative version would be nice..

            # FIXME should be more defensive, i.e. each tweet
            for t in map(json.loads, tfile.read_text().splitlines()):
                user = t['username']
                text = t['tweet']
                lang = t.get('language')

                if lang in IGNORE_LANGUAGES:
                    continue

                # TODO would be nice to apply this both to the db (at least before rendering)
                # so could work retrospectively

                # one annoying thing is that if the username contains the query, it's gonna return all results
                # still annoying that it's even retrieved... not sure what to do with it; again, iterative search would help
                # seems that even twitter staff suggest to postfilter
                # https://twittercommunity.com/t/exclude-username-when-searching/10653/3
                sq = query.strip("'").strip('""').lower()
                # TODO cli interface should be exact by default? not sure
                if ' ' not in sq: # hacky way to check that it's single worded?
                    # TODO log this? gonna be too spammy, maybe once per user
                    # NOTE: in reply, the usernames *are* in the tweet body, so need to check metdata:
                    reply_to_s = ' '.join(x.get('screen_name', '') + '_' + x.get('name', '') for x in t.get('reply_to', []))
                    if any(sq in x.lower() for x in (
                            user,
                            t.get('name', ''),
                            reply_to_s,
                        )):
                            continue
                            # todo warn somehow? maybe at least a summary
                    # NOTE ^^ aaand.. this is still not enough because if the user was deleted it's not ending up in 'reply_to'...
                    if re.search(fr'@[0-9a-z_]*{re.escape(sq)}', text.lower()):
                        continue

                    # shit. it's really quite fuzzy, e.g. 'memex' might match the username 'mem_ex'. jesus!
                    if sq not in text.lower():
                        continue

                when = datetime.strptime(
                    t['created_at'][:len('2020-11-30 01:24:27')] + ' ' + t['timezone'],
                    '%Y-%m-%d %H:%M:%S %z',
                )
                yield Result(
                    uid=str(t['id']),
                    when=when,
                    link    =t['link'], # TODO generate from id and user?
                    text    =text,
                    user    =user,
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


def test() -> None:
    ts = TwitterSearch()
    res = list(ts.search('"виктор аргонов"', limit=10))
    # todo think about quoting? probably should quote by default?
    for r in res:
        print(r)
    assert len(res) == 10


def main() -> None:
    test()


if __name__ == '__main__':
    main()
