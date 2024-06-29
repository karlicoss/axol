from dataclasses import dataclass
from typing import Literal, Sequence


Kind = Literal[
    'regular',
    'tag',
]


@dataclass
class BasePinboardQuery:
    query: str


# TODO copy paste from github -- think if we can unfy it?
@dataclass
class PinboardQuery(BasePinboardQuery):
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
        # don't search tags by default? at least for now
        # FIXME think about this later
        return kind == 'regular'
