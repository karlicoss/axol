#!/usr/bin/env python3

# https://stackoverflow.com/a/13624858/706389
## todo has some types in kython
class classproperty:
    def __init__(self, f) -> None:
        self.f = f
    def __get__(self, obj, owner):
        return self.f(owner)


from typing import Callable, Dict, List, TypeVar, Iterable

T = TypeVar('T')
K = TypeVar('K')

def group_by_key(l: Iterable[T], key: Callable[[T], K]) -> Dict[K, List[T]]:
    res: Dict[K, List[T]] = {}
    for i in l:
        kk = key(i)
        lst = res.get(kk, [])
        lst.append(i)
        res[kk] = lst
    return res


from typing import Any
Json = Dict[str, Any]

# todo ugh. this isn't gonna work because some things are unhashable
# from more_itertools import one
# def the(it):
#     return one(set(it)) # meh

from typing import Iterable
A = TypeVar('A')

def the(l: Iterable[A]) -> A:
    it = iter(l)
    try:
        first = next(it)
    except StopIteration as ee:
        raise RuntimeError('Empty iterator?')
    assert all(e == first for e in it)
    return first
