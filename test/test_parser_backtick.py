import parsy
import pytest

from psh.parser import command, command_sequence, backtick
from psh.model import Word, ConstantString, Assignment, Command, VarRef, Id, Token, CommandSequence, CommandPipe, While, If
from psh.local import make_env


@pytest.mark.parametrize(("text", "expected"), (
        ("`foo`", Command([Word([
                    CommandSequence([Command([Word([
                        ConstantString("foo")]),
                    ])])])])),
))
def test_backtick(text, expected):
    cmd = command.parse(text)
    assert cmd == expected
    assert cmd.assignments == expected.assignments
    cmd = command_sequence.parse(text)
    assert cmd == CommandSequence([expected])


def test_basic():
    backtick.parse("``")
