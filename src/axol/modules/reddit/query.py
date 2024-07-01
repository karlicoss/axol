from dataclasses import dataclass
from typing import assert_never, Iterator

from axol.core.query import exact, raw, doublequote, _check, Compilable


@dataclass
class SearchQuery:
    query: str


@dataclass
class Query(Compilable[SearchQuery]):
    query: str | raw | exact

    # FIXME ugh some false positives
    # why does it match this???
    # https://www.reddit.com/r/bloxfruits/search?q=memex&restrict_sr=on
    # yeah, so for 'memex' it definitely feels like makes sense to filter out
    # perhaps do a magic recursive filtering, literally checking inside the object?
    # probably best to do it at search time
    # that way could reuse the same code both before inserting in the db and during retrieval

    # FIXME port EXCLUDED_SUBREDDIT from old axol?
    # FIXME port domain: search fold old axol?

    # NOTE: seems like it might find things not necessarily in link/username/body etc
    # e.g. "bret victor" results in
    # https://www.reddit.com/r/ObsidianMD/comments/17cbhxj/doh_never_realised_this_had_to_share/
    # which has "bret victor" on the image.. so maybe their search engine is searching other stuff too
    # just in case I decide implement some post-search filtering

    def compile(self) -> Iterator[SearchQuery]:
        query = self.query
        match query:
            case raw(q):
                yield SearchQuery(query=q)
            case exact(q) | str(q):
                # NOTE: without quoting, seems to work as OR
                # e.g. bret victor matches bret and victor separately
                # NOTE: even single words might return slightly different results with or without quotes
                # e.g. "memex" vs memex
                # but seems to be a negligible difference (not sure how it manifests though)
                yield SearchQuery(query=doublequote(_check(q)))
            case _:
                assert_never(query)
