def reddit_link(s: str) -> str:
    assert s.startswith('/'), s
    return f'https://reddit.com{s}'
