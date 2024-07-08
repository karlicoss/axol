from dataclasses import dataclass
from datetime import datetime

import orjson

from axol.core.common import datetime_aware, _check


# todo use parent_id?
@dataclass
class Base:
    id: str
    created_at: datetime_aware
    author: str

    @property
    def permalink(self) -> str:
        return f'https://news.ycombinator.com/item?id={self.id}'


@dataclass
class Comment(Base):
    text: str


@dataclass
class Story(Base):
    title: str
    url: str | None  # might be mising if it's an "ask hn" or smth like that
    text: str | None  # might be missing if it's a link submission
    points: int
    num_comments: int


Result = Comment | Story


# todo add uid here? not sure it should be inside the entity...
def parse(data: bytes) -> Result:
    j = orjson.loads(data)

    entity_types = []
    if 'comment_text' in j:
        entity_types.append('comment')
    if j['objectID'] == str(j['story_id']):  # uhh, story_id is int
        # NOTE: story_text isn't always present!
        # e.g. if it's just a submitted link
        entity_types.append('story')
    assert len(entity_types) == 1, (entity_types, j)
    [entity_type] = entity_types

    ignore = [
        'created_at_i',  # there is created_at which has the date
        'updated_at',  # we don't use that
        'parent_id',  # we don't use this, maybe later
        'children',  # TODO might be useful to handle later?
        # NOTE: children isn't the same thing as the number of comments
    ]
    if entity_type == 'comment':
        ignore.extend(
            [
                ## these aren't useful for comments (yet?)
                'story_id',
                'story_title',
                'story_url',
                ##
            ]
        )
    elif entity_type == 'story':
        ignore.extend(
            [
                'story_id',  # same as object_id
            ]
        )
    else:
        raise RuntimeError(j)

    for k in ignore:
        j.pop(k, None)

    author = _check(j.pop('author'), str)
    object_id = j.pop('objectID')

    created_at_s = j.pop('created_at')
    created_at = datetime.fromisoformat(created_at_s)
    assert created_at.tzinfo is not None, created_at_s

    result: Result
    if entity_type == 'comment':
        comment_text = _check(j.pop('comment_text'), str)
        points = j.pop('points', None)
        # ugh. sometimes points isn't present, but when they do, they are none?
        assert points is None
        result = Comment(
            id=object_id,
            created_at=created_at,
            author=author,
            text=comment_text,
        )
    elif entity_type == 'story':
        # TODO maybe use pydantic for such validation??
        _story_text = j.pop('story_text', None)
        # sometimes it's not present, sometimes present but empty
        story_text = None if len(_story_text or '') == 0 else _story_text
        num_comments = _check(j.pop('num_comments'), int)
        points = _check(j.pop('points'), int)
        title = _check(j.pop('title'), str)
        _url = j.pop('url', None)
        # seems that sometimes (not always!) url is present but empty for things like "ask hn"
        url = None if len(_url or '') == 0 else _url
        result = Story(
            id=object_id,
            created_at=created_at,
            author=author,
            title=title,
            url=url,
            text=story_text,
            points=points,
            num_comments=num_comments,
        )
    else:
        raise RuntimeError(entity_type)

    # todo make more defensive later?
    assert len(j) == 0, j

    return result
