import pytest

from psh.parser import command_sequence
from psh.model import Word, Id, CommandSequence, Command, Case
from psh.glob import STAR


w = lambda w: Word([Id(w)])
a = w("a")
x = w("x")
cmd = lambda *cs: CommandSequence([Command([*cs])])


@pytest.mark.parametrize(("text", "expected"), (
    ("case a in esac", CommandSequence([
        Case(a)
    ])),
    ("case a in (x) ;; esac", CommandSequence([
        Case(a).with_case(x, CommandSequence([]))
    ])),
    ("case a in x) foo ;; *) bar;; esac", CommandSequence([
        Case(a).with_case(x, cmd(w("foo")))
               .with_case(Word([STAR]), cmd(w("bar")))
    ])),
    ("case a in\nx)\nfoo\n;;\n*)\nbar;;\nesac", CommandSequence([
        Case(a).with_case(x, cmd(w("foo")))
               .with_case(Word([STAR]), cmd(w("bar")))
    ])),
), ids=lambda x: x.replace(" ", "_") if isinstance(x, str) else x)
def test_basic(text, expected):
    cmd = command_sequence.parse(text)
    assert cmd == expected
