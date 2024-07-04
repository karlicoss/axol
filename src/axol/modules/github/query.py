# TODO merge commits are kinda annoying?
from dataclasses import dataclass
from typing import assert_never, Iterator, Literal, Sequence, get_args

from axol.core.query import exact, raw, doublequote, _check, Compilable


Kind = Literal[
    'repositories',
    'issues',
    'commits',
    'code',
]


@dataclass
class SearchQuery:
    query: str
    kind: Kind


@dataclass
class Query(Compilable[SearchQuery]):
    query: str | raw | exact
    included: Sequence[Kind] | None = None
    excluded: Sequence[Kind] | None = None

    def compile(self) -> Iterator[SearchQuery]:
        all_kinds: list[Kind] = list(get_args(Kind))

        included = self.included
        excluded = self.excluded
        assert not (included is not None and excluded is not None)
        if included is not None:
            kinds = [kind for kind in all_kinds if kind in included]
        elif excluded is not None:
            kinds = [kind for kind in all_kinds if kind not in excluded]
        else:
            kinds = all_kinds
        assert len(kinds) > 0, self  # just in case

        query = self.query
        qq: str
        match query:
            case raw(q):
                qq = q
            case exact(q) | str(q):
                # NOTE: if we don't quote, it seems to match as OR
                # e.g. bret victor matches just "victor" here https://github.com/milonmaze/privacy-terms-observatory-beta/issues/34
                #
                # even for single term stuff might make sense
                # e.g. searching github.com/karlicoss might match mentions of @karlicoss
                # FIXME would be good to double check and see if string that we search is present inside?
                # NOTE: e.g. for issue search, the match might be from one of the comments in discussion
                # in case we decide to filter on the client side
                #
                #  TODO ugh. for "extended mind" in quotes github still seems to do some sort of fuzzy search??
                # e.g. matches this
                # https://github.com/python/cpython/issues/35935
                # basically check this -- lots of completely unrelated matches
                # https://github.com/search?q=%22extended+mind%22&type=issues&s=created&o=asc
                qq = doublequote(_check(q))
            case _:
                assert_never(query)

        for kind in kinds:
            yield SearchQuery(query=qq, kind=kind)


def test() -> None:
    assert list(Query('just testing', included=['commits', 'issues']).compile()) == [
        SearchQuery('"just testing"', kind='issues'),
        SearchQuery('"just testing"', kind='commits'),
    ]

    assert list(Query('whatever', excluded=['code']).compile()) == [
        SearchQuery('"whatever"', kind='repositories'),
        SearchQuery('"whatever"', kind='issues'),
        SearchQuery('"whatever"', kind='commits'),
    ]
