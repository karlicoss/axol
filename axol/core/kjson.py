from typing import List


from datetime import datetime
# TODO don't really like it...
def _date2str(dt: datetime) -> str:
    return dt.isoformat()


import dateutil.parser
def _str2date(s: str) -> datetime:
    # TODO also isoformat??
    # yep, it looks like the easiest way to parse iso formatted date...
    return dateutil.parser.parse(s)


class ToFromJson:
    # TODO additional way to specify date fields?
    def __init__(self, cls, as_dates: List[str]) -> None:
        self.cls = cls
        self.dates = as_dates

    def to(self, obj):
        res = obj._asdict()
        for k in res:
            v = res[k]
            if k in self.dates:
                res[k] = _date2str(v)

        # make sure it's actually inverse
        inv = self.from_(res)
        assert obj == inv
        return res

    def from_(self, jj):
        res = {}
        for k in jj:
            v = jj[k]
            if k in self.dates:
                res[k] = _str2date(v)
            else:
                res[k] = v
        return self.cls(**res)
