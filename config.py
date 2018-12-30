from typing import List, Iterator

def pintag(query: str) -> List[str]:
    # https://pinboard.in/howto/#tags
    return list({
        f'tag:{query.replace(" ", "-")}',
        f'tag:{query.replace(" ", "_")}',
    })


def pinboard_quote(s: str):
    # shit, single quotes do not work right with pinboard..
    if s.startswith("'"):
        return s
    return f'"{s}"'


# TODO protocol?..
class Pinboard:
    def __init__(self, name: str, queries: List[str], quote=True):
        self.name = name
        if quote:
            self.queries = list(map(pinboard_quote, queries))
        else:
            self.queries = queries
    # TODO how to make it unique and fs safe??

    def __repr__(self):
        return str(self.__dict__)




P = Pinboard


def make_pinboard() -> Iterator[Pinboard]:
    yield P('arbtt', [
        'arbtt',
    ])

    emind = 'extended mind'
    yield P('extended mind', [
        emind,
        *pintag(emind),
    ])

    ll = 'lifelogging'
    yield P('lifelogging', [
        ll, *pintag(ll),
    ])

    openbci = 'openbci'
    yield P('openbci', [
        openbci, *pintag(openbci),
    ])

    pkm = 'personal knowledge management'
    yield P('pkm', [
        'pkm', *pintag('pkm'),
        pkm, *pintag(pkm),
    ])

    qg = 'quantum gravity'
    yield P('quantum gravity', [
        qg, *pintag(qg),
    ])

    # TODO warn about duplicate?
    qs = 'quantifield self'
    yield P('quantified self', [
        'quantified-self',
        qs, *pintag(qs),
    ])

pinboard = list(make_pinboard())


del P
