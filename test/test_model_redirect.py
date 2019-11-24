import os
import pytest

from psh.model import Redirect, Redirects, RedirectTo, RedirectFrom, RedirectDup, ConstantString
from psh.builtin import Env
from psh.parser import redirects

from .os import Os


@pytest.mark.parametrize(
    ("rds", "during"),
    (
        ("",
         {0: Os.STDIN, 1: Os.STDOUT, 2: Os.STDERR}),
        ("</dev/null",
         {0: ("/dev/null", os.O_RDONLY), 1: Os.STDOUT, 2: Os.STDERR, 100: Os.STDIN}),
        ("0<&-",
         {1: Os.STDOUT, 2: Os.STDERR, 100: Os.STDIN}),
        ("0<&- 3<&-",
         {1: Os.STDOUT, 2: Os.STDERR, 100: Os.STDIN}),
        ("1>&2",
         {0: Os.STDIN, 1: Os.STDERR, 2: Os.STDERR, 100: Os.STDOUT}),
        ("1>&2 2>&1",
         {0: Os.STDIN, 1: Os.STDERR, 2: Os.STDERR, 100: Os.STDOUT, 101: Os.STDERR}),
        ("1>&2 1>&-",
         {0: Os.STDIN, 2: Os.STDERR, 100: Os.STDOUT}),
        ("1>&2 2>&-",
         {0: Os.STDIN, 1: Os.STDERR, 100: Os.STDOUT, 101: Os.STDERR}),
    ), ids=lambda x: x.replace(" ", "_") if isinstance(x, str) else None)
def test_redirect(rds, during):
    o = Os()
    fds = dict(o.fds)
    parsed = redirects.parse(rds)
    r = Redirects().with_redirect(*parsed)
    e = Env()
    with o.patch():
        with Redirect.activate(e, r) as s:
            assert o.fds == during
        assert o.fds == fds
