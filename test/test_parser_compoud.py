import pytest

from psh.parser import command_sequence
from psh.model import Word, ConstantString, Command, VarRef, Id, Token, CommandSequence, CommandPipe, While, If


echo = CommandSequence([Command([Word([Id("echo")])])])


@pytest.mark.parametrize(("text", "expected"), (
        ("{}", CommandSequence([])),
        ("echo {}", CommandSequence([Command([Word([Id("echo")]), Word([ConstantString("{}")])])])),
        ("{ echo }", CommandSequence([echo])),
        ("{ ; echo ; }", CommandSequence([echo])),
        ("{\n echo \n }", CommandSequence([echo])),
), ids=lambda x: x.replace(" ", "_").replace("\n", "%") if isinstance(x, str) else None)
def test_basic(text, expected):
    cmd = command_sequence.parse(text)
    assert cmd == expected
