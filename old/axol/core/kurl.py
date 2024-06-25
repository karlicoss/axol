import re

# TODO use something standard?...

def is_garbage(s: str) -> bool:
    return False


def test():
    GARB = """
.hq2oYG2r0
.ahVKXPXKOa
.wbBaZYJJ0N
.fpNG0gygY
.rxB9e2V5r
.ymeD5MpGYv
.xxg40lKLP
.ffqrG9K1A
.graK0lwdN8
.djJ7JJ04B
.fmX3AbjNk
.rvn7zvQZD5
.mdQRPaRl6
.tcPMrxg1w
.vbMk5P9BM
.coAp9WlE3
.qpx3Wqb6Ge
.oeJN1OGAvo
.goGrm1vBk
.pt65k1q
.ihrXeD8bY
.xh1dYDg1J
.prMq2xPvY
.abnk750Ov
.cdpyNM3kQ
.clD4bKWRG
.clD4bKWRG
.iyG4WYwwo
.ck7Zq1Z8RM
.gq6W6j9Dg9
.ydYvjbG2z
.leMml2J0ML
.ar2Q3ANW2
.dqdvxmGZnw
.anpbyxGk5
.vx2w1XQ6R
.qexDBPVEz
.tdppr3emd
.ecdqqiddz
.hv45x4be7
.ninj2gb3r
.ofacw8w8t
.tb75y0jbx
.8dy0f0uwx
.8dy0f0uwx
.smhvdpcds
.vbm877fms
""".strip('\n').splitlines()

    NON_GARB = """
# TODO ugh. not sure how to do that properly..
    """

    print(GARB)

def lchop(chop: str, s: str) -> str:
    if s.startswith(chop):
        return s[len(chop):]
    return s

def normalise(u: str) -> str:
    for p in (
            'http://',
            'https://',
            'www.',
    ):
        u = lchop(p, u)

    idish = re.search(r'(.*)#(.*)', u)
    if idish is not None:
        u = idish.group(1)
        # ii = idish.group(1)
        # TODO check for none??

    u = u.rstrip('/')
    return u
