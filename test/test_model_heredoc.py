import pytest

from psh.model import Command, RedirectHere, Word, Id, ConstantString
from psh.local import make_env


def test_run_a_command():
    cmd = Command([Id("cat")]).with_redirect(
        RedirectHere(content=Word([ConstantString("this is a heredoc")])))
    env = make_env()

    assert cmd.evaluate(env) == "this is a heredoc"
