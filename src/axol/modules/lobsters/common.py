def extract_uid(soup) -> str:
    # NOTE ugh. so there is id and data-shortid
    # for stories , id is story_{sid} and data-shortid is {sid}. the permalink is lobste.rs/s/{sid}
    # for comments, id is c_{cid}     and data-shortid is {cid}. the permalink is lobste.rs/s/{sid}#c_{cid}. just #{cid} isn't working
    # in addition, not sure if {sid} and {cid} namespaces can overlap (they look kinda similar)
    # I guess kinda makes sense to keep it consistent with external links
    # so for stories, uid is gonna be {sid}, for comments, c_{cid}
    short_id: str = soup.attrs['data-shortid']
    _id: str = soup.attrs['id']
    if _id == f'story_{short_id}':
        return short_id
    elif _id == f'c_{short_id}':
        return _id
    else:
        raise RuntimeError(f'unexpected combination: {short_id=} {_id=}')


def lobsters(s: str) -> str:
    assert s.startswith('/s/'), s
    return f'https://lobste.rs{s}'
