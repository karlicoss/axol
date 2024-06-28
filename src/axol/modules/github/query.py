from dataclasses import dataclass
from typing import Literal, Sequence


Kind = Literal[
    'repositories',
    'issues',
    'commits',
    'code',
]


@dataclass
class BaseGithubQuery:
    query: str


@dataclass
class GithubQuery(BaseGithubQuery):
    included: Sequence[Kind] | None = None
    excluded: Sequence[Kind] | None = None

    def __post_init__(self) -> None:
        assert not (self.included is not None and self.excluded is not None)

    def include(self, kind: Kind) -> bool:
        included = self.included
        excluded = self.excluded
        if included is not None:
            return kind in included
        if excluded is not None:
            return kind not in excluded
        return True
