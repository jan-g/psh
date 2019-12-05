import pytest

from .test_glob import make_dirs, cwd

from psh.model import Command, Word, Id
from psh.glob import STAR
from psh.local import make_env


def test_run_a_command():
    cmd = Command([
        Word([Id("echo")]),
        Word([STAR]),
    ])
    env = make_env()

    with make_dirs("a", "b", "c", "d", "e") as d:
        with cwd(d):
            assert cmd.evaluate(env) == "a b c d e"
