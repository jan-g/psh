import pytest

from psh.parser import command, command_sequence, ParseError
from psh.model import (Word, ConstantString, Command, VarRef, Id, Token,
                       CommandSequence, CommandPipe, While, If,
                       RedirectFrom, RedirectTo, RedirectDup, RedirectHere)


cat = lambda: Command([Word([Id("cat")])])


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("0</dev/null cat", cat().with_redirect(RedirectFrom(0, ["/dev/null"]))),
        ("1>/dev/null cat", cat().with_redirect(RedirectTo(1, ["/dev/null"]))),
        ("2>>/dev/null cat", cat().with_redirect(RedirectTo(2, ["/dev/null"], append=True))),
        ("3>&- cat", cat().with_redirect(RedirectDup(3, ["-"]))),
        ("0<&- cat", cat().with_redirect(RedirectDup(0, ["-"]))),
        ("2>&1 cat", cat().with_redirect(RedirectDup(2, ["1"]))),
        ("0<&6 cat", cat().with_redirect(RedirectDup(0, ["6"]))),
        ("</dev/null cat", cat().with_redirect(RedirectFrom(0, ["/dev/null"]))),
        (">/dev/null cat", cat().with_redirect(RedirectTo(1, ["/dev/null"]))),
        (">>/dev/null cat", cat().with_redirect(RedirectTo(1, ["/dev/null"], append=True))),
        (">&- cat", cat().with_redirect(RedirectDup(1, ["-"]))),
        ("<&- cat", cat().with_redirect(RedirectDup(0, ["-"]))),
        (">&2 cat", cat().with_redirect(RedirectDup(1, ["2"]))),
        ("<&6 cat", cat().with_redirect(RedirectDup(0, ["6"]))),
        ("cat <<'EOF'\nhello $world\nEOF\n", cat().with_redirect(
            RedirectHere(end="EOF", quote="'", content=ConstantString("hello $world\n")))),
        ("cat <<\"EOF\"\nhello $world\nEOF\n", cat().with_redirect(
            RedirectHere(end="EOF", quote='"', content=ConstantString("hello $world\n")))),
        ("cat <<EOF\nhello $world\nEOF\n", cat().with_redirect(
            RedirectHere(end="EOF",
                         content=Word([
                             ConstantString("hello "),
                             VarRef("world", double_quoted=True),
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
