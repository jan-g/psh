import io
import logging
import tempfile

from psh.parser import command
from psh.model import Word, ConstantString, Command, Id, CommandSequence, CommandPipe, While, If, Function, VarRef
from psh.builtin import make_env

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
