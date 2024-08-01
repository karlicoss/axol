def pinboard_link(s: str) -> str:
    assert s.startswith('/'), s
    return f'https://pinboard.in{s}'
