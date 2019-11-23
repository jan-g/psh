import pytest

from psh.parser import command_sequence
from psh.model import Word, ConstantString, Command, VarRef, Id, Token, CommandSequence, Function


@pytest.mark.parametrize(("text", "expected"), (
        ("f() { echo }",
         CommandSequence([
             Function(Id("f"), CommandSequence([Command([Word([Id("echo")])])]))
         ])),
), ids=lambda x: x.replace(" ", "_").replace("\n", "%") if isinstance(x, str) else None)
def test_basic(text, expected):
    cmd = command_sequence.parse(text)
    assert cmd == expected
