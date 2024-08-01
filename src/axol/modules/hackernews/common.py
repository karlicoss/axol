def hn_link(s: str) -> str:
    assert s.startswith('/'), s
    return f'https://news.ycombinator.com{s}'
