import logging

from psh.model import (Word, ConstantString, Token, Id, VarRef,
                       Command, CommandSequence, CommandPipe, While, If, Function)
from psh.local import make_env

LOG = logging.getLogger(__name__)


def test_invoke_a_function():
    env = make_env()
    env.functions["f"] = Function(Id("f"), CommandSequence([
        Command([Word([Id("echo")]), Word([VarRef("1")])])
    ]))

    cmd = CommandSequence([
        Command([Word([Id("f")]), Word([ConstantString("hello world")])]),
    ])

    assert cmd.evaluate(env) == "hello world"


def test_locals():
    env = make_env()
    env['x'] = "1"
    env.functions["f"] = Function(Id("f"), CommandSequence([
        Command([Word([Id("local")]), Word([Id("x"), Token("="), VarRef("1")])]),
        Command([Word([Id("echo")]), Word([VarRef("x")])]),
    ]))

    cmd = CommandSequence([
        Command([Word([Id("f")]), Word([ConstantString("hello world")])]),
    ])

    assert cmd.evaluate(env) == "hello world"
    assert env['x'] == "1"
