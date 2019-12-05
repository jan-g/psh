import pytest

from psh.parser import command_sequence
from psh.model import Word, ConstantString, Command, CommandSequence
from psh.glob import STAR, STARSTAR


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ('"*"', CommandSequence([Command([Word([ConstantString("*")], double_quoted=True)])])),
        ("'*'", CommandSequence([Command([Word([ConstantString("*")], double_quoted=False)])])),
        ('\\*', CommandSequence([Command([Word([ConstantString("*")], double_quoted=False)])])),
        ('*', CommandSequence([Command([Word([STAR], double_quoted=False)])])),
    ), ids=lambda x: x.replace(" ", "_").replace('"', '%') if isinstance(x, str) else None)
def test_dq(text, expected):
    assert command_sequence.parse(text) == expected
