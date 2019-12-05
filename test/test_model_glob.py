import pytest

from .test_glob import make_dirs, cwd, TOUCH

from psh.model import Command, Word, Id, ConstantString
from psh.local import make_env
from psh.glob import STAR


def test_run_a_command():
    cmd = Command([
        Word([Id("echo")]),
        Word([STAR]),
    ])
    env = make_env()

    with make_dirs("a", "b", "c", "d", "e") as d:
        with cwd(d):
            assert cmd.evaluate(env) == "a b c d e"


def test_fixed_pieces():
    cmd = Command([
        Word([Id("echo")]),
        Word([STAR, ConstantString("/..")]),
    ])
    env = make_env()

    with make_dirs("a", "b", "c", "d", TOUCH, "e", "f", "g") as d:
        with cwd(d):
            assert cmd.evaluate(env) == "a/.. b/.. c/.. d/.."
