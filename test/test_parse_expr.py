import parsy
import pytest

from psh.parser import expr
from psh.local import make_env


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("a", 1),
        ("((b))", 2),
        ("(( ( ( cd ) ) ))", 3),
        ("a * b * cd", 6),
        ("cd * cd / b", 4.5),
        ("(8 * 8) / 8 / 8", 1),
        ("5-4-3", -2),
    ), ids=lambda x: x.replace(" ", "_") if isinstance(x, str) else None)
def test_expr(text, expected):
    env = make_env()
    env.update({"a": 1,
                "b": 2,
                "cd": 3})

    assert expr.parse(text)(env) == expected
