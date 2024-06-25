from contextlib import contextmanager

import dominate  # type: ignore[import]


# TODO shit. contextmanager is bound to thread...
# https://github.com/Knio/dominate/issues/108
# TODO perhaps post on github?
# TODO FIXME implement a test or something...
# TODO generate random?
# TODO remove context after finishing?
@contextmanager
def hack_html_context(uid: str):
    domtag = dominate.dom_tag
    prev = domtag._get_thread_context
    def hacked_thread_contex(uid=uid):
        return uid

    try:
        domtag._get_thread_context = hacked_thread_contex
        yield
    finally:
        domtag._get_thread_context = prev


@contextmanager
def adhoc_html(uid: str, cb):
    with hack_html_context(uid=uid):
        with dominate.tags.html() as html:
            # TODO not sure if original html would ever be useful?
            yield # TODO needs a test..
        # TODO meh..
        cb(html.children)
