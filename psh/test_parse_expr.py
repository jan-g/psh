import parsy
import pytest

from .parser import expr
from .builtin import make_env


def test_expr():
    env = make_env()
    env.update({"a": 1,
                "b": 2,
                "cd": 3})

    assert expr.parse("a")(env) == 1
    assert expr.parse("((b))")(env) == 2
    assert expr.parse("(( ( ( cd ) ) ))")(env) == 3

    assert expr.parse("a * b * cd")(env) == 6
    assert expr.parse("cd * cd / b")(env) == 4.5

    assert expr.parse("(8 * 8) / 8 / 8")(env) == 1

    assert expr.parse("5-4-3")(env) == -2
