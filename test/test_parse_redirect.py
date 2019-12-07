import pytest

from psh.parser import command, command_sequence, ParseError
from psh.model import (Word, ConstantString, Command, VarRef, Id, Token,
                       CommandSequence, CommandPipe, While, If,
                       RedirectFrom, RedirectTo, RedirectDup, RedirectHere)


cat = lambda: Command([Word([Id("cat")])])
w = lambda w: Word([ConstantString(w)])
devnull = w("/dev/null")


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("0</dev/null cat", cat().with_redirect(RedirectFrom(0, devnull))),
        ("1>/dev/null cat", cat().with_redirect(RedirectTo(1, devnull))),
        ("2>>/dev/null cat", cat().with_redirect(RedirectTo(2, devnull, append=True))),
        ("3>&- cat", cat().with_redirect(RedirectDup(3, w("-")))),
        ("0<&- cat", cat().with_redirect(RedirectDup(0, w("-")))),
        ("2>&1 cat", cat().with_redirect(RedirectDup(2, w("1")))),
        ("0<&6 cat", cat().with_redirect(RedirectDup(0, w("6")))),
        ("</dev/null cat", cat().with_redirect(RedirectFrom(0, devnull))),
        (">/dev/null cat", cat().with_redirect(RedirectTo(1, devnull))),
        (">>/dev/null cat", cat().with_redirect(RedirectTo(1, devnull, append=True))),
        (">&- cat", cat().with_redirect(RedirectDup(1, w("-")))),
        ("<&- cat", cat().with_redirect(RedirectDup(0, w("-")))),
        (">&2 cat", cat().with_redirect(RedirectDup(1, w("2")))),
        ("<&6 cat", cat().with_redirect(RedirectDup(0, w("6")))),
        ("cat <<'EOF'\nhello $world\nEOF\n", cat().with_redirect(
            RedirectHere(end="EOF", quote="'", content=ConstantString("hello $world\n")))),
        ("cat <<\"EOF\"\nhello $world\nEOF\n", cat().with_redirect(
            RedirectHere(end="EOF", quote='"', content=ConstantString("hello $world\n")))),
        ("cat <<EOF\nhello $world\nEOF\n", cat().with_redirect(
            RedirectHere(end="EOF",
                         content=Word([
                             ConstantString("hello "),
                             VarRef(ConstantString("world"), double_quoted=True),
                             ConstantString("\n"),
                         ], double_quoted=True)))),
        ("cat <<'EOF'\nhello $world\nEOF", cat().with_redirect(
            RedirectHere(end="EOF", quote="'", content=ConstantString("hello $world\n")))),
    ), ids=lambda x: x.replace(" ", "_").replace("'", "*") if isinstance(x, str) else None)
def test_basic(text, expected):
    cmd = command_sequence.parse(text)
    assert cmd == CommandSequence([expected])


@pytest.mark.parametrize("text",
(
    "cat <<'EOF'\nhello $world\n",
    "cat <<\"EOF\"",
    "cat <<EOF",
    "cat <<'EOF'\nEO",
), ids = lambda x: x.replace(" ", "_").replace("'", "*") if isinstance(x, str) else None)
def test_throws(text):
    with pytest.raises(ParseError):
        cmd = command_sequence.parse(text)


def test_while():
    for i, o in (
            ("0</dev/null while a; do b; done >>/tmp/x",
                CommandSequence([While(
                    CommandSequence([Command([Word([ConstantString("a")])])]),
                    CommandSequence([Command([Word([ConstantString("b")])])]),
                ).with_redirect(RedirectFrom(0, devnull), RedirectTo(1, w("/tmp/x"), append=True))])),
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
                ]).with_redirect(RedirectFrom(0, devnull), RedirectTo(1, w("/tmp/x"), append=True))])),
    ):
        cmd = command_sequence.parse(i)
        assert cmd == o
        assert cmd.redirects == o.redirects
