import pytest

from .parser import command, command_sequence
from .model import (Word, ConstantString, Command, VarRef, Id, Token,
                    CommandSequence, CommandPipe, While, If,
                    RedirectFrom)
from .builtin import Env, make_env


def test_basic():
    for i, o in (
                ("1</dev/null cat", Command([Word([ConstantString("cat")])]).
                                    with_redirect(RedirectFrom(1, "/dev/null"))),
    ):
        cmd = command.parse(i)
        assert cmd == o
        assert cmd.redirects == o.redirects
