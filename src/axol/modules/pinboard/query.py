from dataclasses import dataclass
from typing import assert_never, Iterator, Literal

from axol.core.query import exact, raw, doublequote, _check, Compilable, compile_queries


Kind = Literal[
    'regular',
    'tag',
]


@dataclass
class SearchQuery:
    query: str
    kind: Kind


@dataclass
class Query(Compilable[SearchQuery]):
    # NOTE: two words (unquoted) on pinboard seem to work as AND?
    # NOTE: quotes are still a little fuzzy (e.g. wrt punctuation), but words in query are next to each other
    # e.g. compare quoted and unquoted ink by bret victor
    # if not quoted, the words can be spread out in the match
    # it also matches some odd tags:
    # - e.g. '+bret.victor'
    # - or even tag combinations like 'bret', 'victor'

    query: str | raw | exact
    kind: Kind | None = None

    def compile(self) -> Iterator[SearchQuery]:
        query = self.query
        kind = self.kind
        if kind is None:
            # NOTE: looks like if it's a single word there is no point in tag search
            # e.g. search for configurationmanagement
            # TODO unless there are lots of results? so we can fetch them all? not sure..
            yield from Query(query=self.query, kind='regular').compile()

            match query:
                case raw(q):
                    # for raw query don't do anything
                    include_tag = True
                case exact(q) | str(q):
                    include_tag = ' ' in q
                case _:
                    assert_never(query)

            if include_tag:
                yield from Query(query=self.query, kind='tag').compile()
            return

        if kind == 'regular':
            match query:
                case raw(q):
                    yield SearchQuery(query=q, kind=kind)
                case exact(q) | str(q):
                    # todo decide later if we wanna the default be exact or not
                    # I guess doesn't hurt? even for single word queries
                    yield SearchQuery(query=doublequote(_check(q)), kind=kind)
                case _:
                    assert_never(query)
        elif kind == 'tag':
            match query:
                case raw(q):
                    yield SearchQuery(query=q, kind=kind)
                case exact(q):
                    # exact is no-op for tags
                    # TODO check tags anyway?
                    yield SearchQuery(query=q, kind=kind)
                case str(q):
                    # NOTE for multi word queries, search doesn't match all tags
                    # e.g. "greg egan" vs tag:gregegan or tag:greg_egan or tag:greg-egan

                    # so we want regular search for "greg egan"
                    # and tag seraches for "gregegan" and "greg_egan"

                    qs = sorted({q.replace(' ', repl) for repl in ['', '_', '-']})
                    for q in qs:
                        yield SearchQuery(query=q, kind=kind)
        else:
            assert_never(kind)


def test_queries() -> None:
    def helper(*queries):
        return list(compile_queries(queries))

    # fmt: off
    assert helper(
        # for raw query there is no validation for special characters etc
        Query(raw('greg " egan'), kind='regular'),
    ) == [
        SearchQuery('greg " egan', kind='regular'),
    ]

    assert helper(
        Query(exact('greg egan'), kind='regular'),
    ) == [
        SearchQuery('"greg egan"', kind='regular'),
    ]

    assert helper(
        Query('greg egan', kind='regular'),
    ) == [
        SearchQuery('"greg egan"', kind='regular')
    ]

    assert helper(
        # raw is no-op for tags
        Query(raw('greg_egan'), kind='tag')
    ) == [
        SearchQuery('greg_egan', kind='tag'),
    ]

    assert helper(
        Query('greg_egan', kind='tag'),
    ) == [
        SearchQuery('greg_egan', kind='tag'),
    ]

    # by default, generates different variations for tags
    assert helper(
        Query('greg egan', kind='tag'),
    ) == [
        SearchQuery('greg-egan'  , kind='tag'),
        SearchQuery('greg_egan'  , kind='tag'),
        SearchQuery('gregegan'   , kind='tag'),
    ]

    assert helper(
        Query('greg egan'),
    ) == [
        SearchQuery('"greg egan"', kind='regular'),
        SearchQuery('greg-egan'  , kind='tag'),
        SearchQuery('greg_egan'  , kind='tag'),
        SearchQuery('gregegan'   , kind='tag'),
    ]

    assert helper(
        Query('greg_egan', kind='tag'),
        Query('greg egan'),
        Query('gregory egan', kind='regular')
    ) == [
        SearchQuery('greg_egan'     , kind='tag'),
        SearchQuery('"greg egan"'   , kind='regular'),
        SearchQuery('greg-egan'     , kind='tag'),
        SearchQuery('gregegan'      , kind='tag'),
        SearchQuery('"gregory egan"', kind='regular')
    ]

    # for single word search, don't generate extra tag searches
    assert helper(
        Query('configurationmanagement'),
    ) == [
        SearchQuery('"configurationmanagement"', kind='regular'),
    ]
    # fmt: on
