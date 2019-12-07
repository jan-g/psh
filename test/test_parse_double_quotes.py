import pytest

from psh.parser import command, command_sequence
from psh.model import Word, ConstantString, Command, VarRef, Id, Token, CommandSequence, CommandPipe, While, If


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ('"hello world"', CommandSequence([Command([Word([ConstantString("hello world")], double_quoted=True)])])),
        ('hello" world"', CommandSequence([Command([Word([Id('hello'),
                                                    Word([ConstantString(' world')], double_quoted=True)],
                                                         double_quoted=False)])])),
        ("", CommandSequence([Command([])])),
        ('""', CommandSequence([Command([Word([ConstantString('')], double_quoted=True)])])),
        ('"$a $b"', CommandSequence([Command([Word([
            VarRef(ConstantString("a"), double_quoted=True),
            ConstantString(" "),
            VarRef(ConstantString("b"), double_quoted=True),
        ], double_quoted=True)])])),
    ), ids=lambda x: x.replace(" ", "_").replace('"', '%') if isinstance(x, str) else None)
def test_dq(text, expected):
    assert command_sequence.parse(text) == expected
