from collections import Counter
from datetime import datetime

from ..feed import Feed


Key = tuple[str, str]

# todo later maybe feeds/models could define stuff to exclude?
EXCLUDE_KEYS: set[Key] = {
    ('Repository', 'description'),
    ('Repository', 'topics'),
    ('Repository', 'stars'),
    ('Submission', 'ups'),
    ('Submission', 'downs'),
    ('Story', 'points'),
    ('Story', 'num_comments'),
}


def print_stats(*, feed: Feed, threshold: float = 0.01) -> None:
    counters: dict[Key, Counter] = {}

    def count(key: Key, item) -> None:
        if key not in counters:
            counters[key] = Counter()
        counters[key][item] += 1

    total = 0
    for crawl_dt, uid, o in feed.feed():
        if isinstance(o, Exception):
            raise o
        total += 1

        d = vars(o)
        d = {k: v for k, v in d.items() if not isinstance(v, datetime)}
        for k, v in d.items():
            kk = (type(o).__name__, k)
            if kk not in EXCLUDE_KEYS:
                count(kk, v)

    printed = False
    for k, c in counters.items():
        for v, cnt in sorted(c.items(), key=lambda p: p[1], reverse=True):
            if cnt / total < threshold:
                continue
            printed = True
            print(f'{str(k):<10} {cnt:<5} {repr(v)}')
    if not printed:
        print(f"No significant outliers! Try increasing threshold from {threshold}")
