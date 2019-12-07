import pytest

from psh.parser import command_sequence
from psh.model import Word, Id, CommandSequence, Command, Case, VarRef, ConstantString
from psh.glob import STAR
from psh.local import make_env


w = lambda w: Word([Id(w)])
a = Word([VarRef(Id("a"))])
echo = lambda out: CommandSequence([Command([Word([Id("echo")]), Word([ConstantString(out)])])])
x = w("x")
cmd = lambda *cs: CommandSequence([Command([*cs])])
star = Word([STAR])


@pytest.mark.parametrize(("cmd", "variable", "expected"), (
    (CommandSequence([Case(a)]), "", ""),
    (CommandSequence([Case(a).with_case(x, echo("foo"))]), "", ""),
    (CommandSequence([Case(a).with_case(x, echo("foo"))]), "y", ""),
    (CommandSequence([Case(a).with_case(x, echo("foo"))]), "x", "foo"),
    (CommandSequence([Case(a).with_case(x, echo("foo")).with_case(star, echo("bar"))]), "", "bar"),
    (CommandSequence([Case(a).with_case(x, echo("foo")).with_case(star, echo("bar"))]), "y", "bar"),
    (CommandSequence([Case(a).with_case(x, echo("foo")).with_case(star, echo("bar"))]), "x", "foo"),
), ids=lambda x: x.replace(" ", "_") if isinstance(x, str) else x)
def test_basic(cmd, variable, expected):
    env = make_env()
    env["a"] = variable
    assert cmd.evaluate(env) == expected
