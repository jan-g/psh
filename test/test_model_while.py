import io
import logging
import tempfile

from psh.parser import command
from psh.model import Word, ConstantString, Command, VarRef, Id, Token, CommandSequence, CommandPipe, While, If
from psh.local import make_env

LOG = logging.getLogger(__name__)


def test_while():
    up = 0
    down = 3

    def count_down(*args, env=None, stdin=None, stdout=None, stderr=None):
        nonlocal down
        stdout.write(b"DOWN\n")
        if down <= 0:
            return 1
        down -= 1
        return 0

    def count_up(*args, env=None, stdin=None, stdout=None, stderr=None):
        nonlocal up
        stdout.write(b"UP\n")
        up += 1
        return 0

    cmd = While(
        Command([Word([Id("down")])]),
        Command([Word([Id("up")])])
    )
    env = make_env()
    env.builtins.update({"up": count_up,
                         "down": count_down})
    out = io.BytesIO()

    assert cmd.execute(env, output=out) == 1
    assert up == 3
    assert out.getvalue().decode("utf-8") == "DOWN\nUP\nDOWN\nUP\nDOWN\nUP\nDOWN\n"


def test_break():
    up = 0
    down = 3

    def count_down(*args, env=None, stdin=None, stdout=None, stderr=None):
        nonlocal down
        stdout.write(b"DOWN\n")
        if down <= 0:
            return 0
        down -= 1
        return 1

    def count_up(*args, env=None, stdin=None, stdout=None, stderr=None):
        nonlocal up
        stdout.write(b"UP\n")
        up += 1
        return 0

    cmd = While(
        Command([Word([Id("up")])]),
        If([(Command([Word([Id("down")])]),
             Command([Word([Id("break")])]))])
    )
    env = make_env()
    env.builtins.update({"up": count_up,
                         "down": count_down})

    out = io.BytesIO()
    assert cmd.execute(env, output=out) == 0
    assert up == 4
    assert out.getvalue().decode("utf-8") == "UP\nDOWN\nUP\nDOWN\nUP\nDOWN\nUP\nDOWN\n"
