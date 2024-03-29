import os
import pytest

from psh.model import Redirect, Redirects
from psh.builtin import Env
from psh.parser import redirects, command

from .mock_os import Os


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
    parsed = command.parse(rds)
    e = Env()
    with o.patch():
        with Redirect.activate(e, parsed) as s:
            assert o.fds == during
        assert o.fds == fds


@pytest.mark.parametrize(
    ("rd1", "rd2", "during"),
    (
        ("", "",
         {0: Os.STDIN, 1: Os.STDOUT, 2: Os.STDERR}),
        ("</dev/null", "",
         {0: ("/dev/null", os.O_RDONLY), 1: Os.STDOUT, 2: Os.STDERR, 100: Os.STDIN}),
        ("0<&-", "",
         {1: Os.STDOUT, 2: Os.STDERR, 100: Os.STDIN}),
        ("0<&-", "3<&-",
         {1: Os.STDOUT, 2: Os.STDERR, 100: Os.STDIN}),
        ("1>&2", "1>&2",
         {0: Os.STDIN, 1: Os.STDERR, 2: Os.STDERR, 100: Os.STDOUT, 101: Os.STDERR}),
        ("1>&2", "2>&1",
         {0: Os.STDIN, 1: Os.STDERR, 2: Os.STDERR, 100: Os.STDOUT, 101: Os.STDERR}),
        ("1>&2", "1>&-",
         {0: Os.STDIN, 2: Os.STDERR, 100: Os.STDOUT, 101: Os.STDERR}),
        ("1>&2", "2>&-",
         {0: Os.STDIN, 1: Os.STDERR, 100: Os.STDOUT, 101: Os.STDERR}),
    ), ids=lambda x: x.replace(" ", "_") if isinstance(x, str) else None)
def test_nested_redirect(rd1, rd2, during):
    o = Os()
    fds = dict(o.fds)
    r1 = Redirects().with_redirect(*redirects.parse(rd1))
    r2 = Redirects().with_redirect(*redirects.parse(rd2))
    e = Env()
    with o.patch():
        with Redirect.activate(e, r1):
            after_first = dict(o.fds)
            with Redirect.activate(e, r2):
                assert o.fds == during
            assert o.fds == after_first
        assert o.fds == fds
