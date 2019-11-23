import io
import logging
import tempfile

from psh.parser import command
from psh.model import Word, ConstantString, Command, VarRef, Id, Token, CommandSequence, CommandPipe, While, If
from psh.builtin import make_env

LOG = logging.getLogger(__name__)


def test_execute():
    env = make_env()
    cmd = command.parse("a=1 b=2 c=$a$b cat /dev/null")
    cmd.evaluate(env)
    assert env['a'] == '1'
    assert env['b'] == '2'
    assert env['c'] == '12'


def test_run_a_command():
    with tempfile.NamedTemporaryFile(mode="w+") as f:
        print("hello world\n", file=f)
        f.flush()
        cmd = command.parse("cat {}".format(f.name))
        env = make_env()
        assert "hello world" == cmd.evaluate(env)


def test_run_a_builtin():
    cmd = command.parse("a=1 b=2 echo $a$b")
    env = make_env()
    assert "12" == cmd.evaluate(env)


def test_run_a_single_pipe():
    with tempfile.NamedTemporaryFile(mode="w+") as f:
        print("hello world", file=f)
        f.flush()
        cmd = CommandPipe([
            Command([Word([Id("cat")]), Word([ConstantString(f.name)])]),
        ])
        env = make_env()
        assert "hello world" == cmd.evaluate(env)


def test_run_a_double_pipe():
    with tempfile.NamedTemporaryFile(mode="w+") as f:
        print("hello world\n", file=f)
        f.flush()
        cmd = CommandPipe([
            Command([Word([Id("cat")]), Word([ConstantString(f.name)])]),
            Command([Word([Id("cat")])]),
        ])
        env = make_env()
        assert "hello world" == cmd.evaluate(env)


def test_run_a_longer_pipe():
    with tempfile.NamedTemporaryFile(mode="w+") as f:
        print("hello world", file=f)
        f.flush()
        cmd = CommandPipe([
            Command([Word([Id("cat")]), Word([ConstantString(f.name)])]),
            Command([Word([Id("tr")]), Word([ConstantString("-d")]), Word([ConstantString("o")])]),
            Command([Word([Id("cat")])]),
        ])
        env = make_env()
        assert "hell wrld" == cmd.evaluate(env)


def test_run_a_builtin_pipe():
    def tr(*args, env=None, stdin=None, stdout=None, stderr=None):
        s = stdin.read().decode("utf-8").replace("e", "E")
        stdout.write(bytes(s, "utf-8"))
        stdout.flush()
        return 0

    with tempfile.NamedTemporaryFile(mode="w+") as f:
        print("hello world", file=f)
        f.flush()
        cmd = CommandPipe([
            Command([Word([Id("cat")]), Word([ConstantString(f.name)])]),
            Command([Word([Id("TR")])]),
            Command([Word([Id("tr")]), Word([ConstantString("-d")]), Word([ConstantString("o")])]),
            Command([Word([Id("cat")])]),
        ])
        env = make_env()
        env.builtins["TR"] = tr
        assert "hEll wrld" == cmd.evaluate(env)


def test_run_a_builtin_pipe_2():
    def tr(*args, env=None, stdin=None, stdout=None, stderr=None):
        s = stdin.read().decode("utf-8").replace("e", "E")
        stdout.write(bytes(s, "utf-8"))
        stdout.flush()
        return 0

    with tempfile.NamedTemporaryFile(mode="w+") as f:
        print("hello world", file=f)
        f.flush()
        cmd = CommandPipe([
            Command([Word([Id("cat")]), Word([ConstantString(f.name)])]),
            Command([Word([Id("tr")]), Word([ConstantString("-d")]), Word([ConstantString("o")])]),
            Command([Word([Id("cat")])]),
            Command([Word([Id("TR")])]),
        ])
        env = make_env()
        env.builtins["TR"] = tr
        assert "hEll wrld" == cmd.evaluate(env)


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


def test_if():
    def pass_after(n):
        def count_down(*args, env=None, stdin=None, stdout=None, stderr=None):
            nonlocal n
            stdout.write(b"C")
            n -= 1
            if n <= 0:
                return 0
            return 1
        return count_down

    def write_const(c):
        def output(*args, env=None, stdin=None, stdout=None, stderr=None):
            stdout.write(bytes(c, "utf-8"))
            return 0
        return output

    env = make_env()
    for letter in "abcdefghijklmnopqrstuvwxyz":
        env.builtins[letter] = write_const(letter)

    for fs, after, expect, res in [("a", 1, "Ca", 0), ("a", 2, "C", 1),
                                   ("ab", 1, "Ca", 0), ("ab", 2, "CCb", 0), ("ab", 3, "CC", 1)]:
        cmd = If([
            (Command([Word([Id("test")])]), Command([Word([Id(f)])]))
            for f in fs])

        env.builtins["test"] = pass_after(after)
        out = io.BytesIO()
        assert cmd.execute(env, output=out) == res
        assert out.getvalue().decode("utf-8") == expect

        if res == 1:
            # Check the else case also
            cmd.append((If.OTHERWISE, Command([Word([Id("z")])])))
            env.builtins["test"] = pass_after(after)
            out = io.BytesIO()
            assert cmd.execute(env, output=out) == 0
            assert out.getvalue().decode("utf-8") == expect + "z"
