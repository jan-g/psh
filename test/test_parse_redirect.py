import pytest

from psh.parser import command, command_sequence
from psh.model import (Word, ConstantString, Command, VarRef, Id, Token,
                       CommandSequence, CommandPipe, While, If,
                       RedirectFrom, RedirectTo, RedirectDup)


cat = Word([ConstantString("cat")])


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("0</dev/null cat", Command([cat]).with_redirect(RedirectFrom(0, ["/dev/null"]))),
        ("1>/dev/null cat", Command([cat]).with_redirect(RedirectTo(1, ["/dev/null"]))),
        ("2>>/dev/null cat", Command([cat]).with_redirect(RedirectTo(2, ["/dev/null"], append=True))),
        ("3>&- cat", Command([cat]).with_redirect(RedirectDup(3, ["-"]))),
        ("0<&- cat", Command([cat]).with_redirect(RedirectDup(0, ["-"]))),
        ("2>&1 cat", Command([cat]).with_redirect(RedirectDup(2, ["1"]))),
        ("0<&6 cat", Command([cat]).with_redirect(RedirectDup(0, ["6"]))),
        ("</dev/null cat", Command([cat]).with_redirect(RedirectFrom(0, ["/dev/null"]))),
        (">/dev/null cat", Command([cat]).with_redirect(RedirectTo(1, ["/dev/null"]))),
        (">>/dev/null cat", Command([cat]).with_redirect(RedirectTo(1, ["/dev/null"], append=True))),
        (">&- cat", Command([cat]).with_redirect(RedirectDup(1, ["-"]))),
        ("<&- cat", Command([cat]).with_redirect(RedirectDup(0, ["-"]))),
        (">&2 cat", Command([cat]).with_redirect(RedirectDup(1, ["2"]))),
        ("<&6 cat", Command([cat]).with_redirect(RedirectDup(0, ["6"]))),
    ), ids=lambda x: x.replace(" ", "_") if isinstance(x, str) else None)
def test_basic(text, expected):
    cmd = command.parse(text)
    assert cmd == expected
    assert cmd.redirects == expected.redirects


def test_while():
    for i, o in (
            ("0</dev/null while a; do b; done >>/tmp/x",
                CommandSequence([While(
                    CommandSequence([Command([Word([ConstantString("a")])])]),
                    CommandSequence([Command([Word([ConstantString("b")])])]),
                ).with_redirect(RedirectFrom(0, ["/dev/null"]), RedirectTo(1, ["/tmp/x"], append=True))])),
    ):
        cmd = command_sequence.parse(i)
        assert cmd == o
        assert cmd.redirects == o.redirects


def test_if():
    for i, o in (
            ("0</dev/null if a; then b; fi >>/tmp/x",
                CommandSequence([If([
                    (CommandSequence([Command([Word([ConstantString("a")])])]),
                     CommandSequence([Command([Word([ConstantString("b")])])]))
                ]).with_redirect(RedirectFrom(0, ["/dev/null"]), RedirectTo(1, ["/tmp/x"], append=True))])),
    ):
        cmd = command_sequence.parse(i)
        assert cmd == o
        assert cmd.redirects == o.redirects
