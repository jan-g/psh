import pytest

from psh.parser import command_sequence
from psh.model import Word, Id, Token, ConstantString, CommandSequence, Command, For, VarRef, RedirectTo, RedirectFrom


w = lambda w: Word([Id(w)])
i = Id("i")
cmds = lambda *cs: CommandSequence([Command([c]) for c in cs])
devnull = Word([ConstantString("/dev/null")])


@pytest.mark.parametrize(("text", "expected"), (
    ("for i; do done", CommandSequence([
        For(i, [VarRef(Token("@"))], CommandSequence([]))
    ])),
    ("for i\ndo\ndone", CommandSequence([
        For(i, [VarRef(Token("@"))], CommandSequence([]))
    ])),
    ("for i in a b c; do foo; done", CommandSequence([
        For(i, [w("a"), w("b"), w("c")], cmds(w("foo")))
    ])),
    (">/dev/null for i in a b c\n\ndo\n\nfoo\n\nbar\n\ndone </dev/null", CommandSequence([
        For(i, [w("a"), w("b"), w("c")], cmds(w("foo"), w("bar")))
            .with_redirect(RedirectTo(1, devnull), RedirectFrom(0, devnull))
    ])),
), ids=lambda x: x.replace(" ", "_") if isinstance(x, str) else x)
def test_basic(text, expected):
    cmd = command_sequence.parse(text)
    assert cmd == expected
