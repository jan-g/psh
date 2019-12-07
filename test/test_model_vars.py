import pytest

from psh.model import Word, ConstantString, VarRef, Id, VarOp
from psh.glob import STAR
from psh.local import make_env


@pytest.mark.parametrize(("pattern", "value", "expected"), (
        (Word([VarRef(ConstantString("a"))]), "xx", "xx"),
        (Word([VarRef(ConstantString("a"), double_quoted=True)], double_quoted=True), "xx yy", "xx yy"),

        (Word([VarOp(VarRef(ConstantString("a")), '#', Word([Id("x")]))]), "xx123xx", "x123xx"),
        (Word([VarOp(VarRef(ConstantString("a")), '#', Word([STAR, Id("x")]))]), "xx123xx", "x123xx"),
        (Word([VarOp(VarRef(ConstantString("a")), '#', Word([Id("x"), STAR]))]), "xx123xx", "x123xx"),
        (Word([VarOp(VarRef(ConstantString("a")), '#', Word([STAR, Id("x"), STAR]))]), "xx123xx", "x123xx"),

        (Word([VarOp(VarRef(ConstantString("a")), '##', Word([Id("x")]))]), "xx123xx", "x123xx"),
        (Word([VarOp(VarRef(ConstantString("a")), '##', Word([STAR, Id("x")]))]), "xx123xx", ""),
        (Word([VarOp(VarRef(ConstantString("a")), '##', Word([Id("x"), STAR]))]), "xx123xx", ""),
        (Word([VarOp(VarRef(ConstantString("a")), '##', Word([STAR, Id("x"), STAR]))]), "xx123xx", ""),

        (Word([VarOp(VarRef(ConstantString("a")), '%', Word([Id("x")]))]), "xx123xx", "xx123x"),
        (Word([VarOp(VarRef(ConstantString("a")), '%', Word([STAR, Id("x")]))]), "xx123xx", "xx123x"),
        (Word([VarOp(VarRef(ConstantString("a")), '%', Word([Id("x"), STAR]))]), "xx123xx", "xx123x"),
        (Word([VarOp(VarRef(ConstantString("a")), '%', Word([STAR, Id("x"), STAR]))]), "xx123xx", "xx123x"),

        (Word([VarOp(VarRef(ConstantString("a")), '%%', Word([Id("x")]))]), "xx123xx", "xx123x"),
        (Word([VarOp(VarRef(ConstantString("a")), '%%', Word([STAR, Id("x")]))]), "xx123xx", ""),
        (Word([VarOp(VarRef(ConstantString("a")), '%%', Word([Id("x"), STAR]))]), "xx123xx", ""),
        (Word([VarOp(VarRef(ConstantString("a")), '%%', Word([STAR, Id("x"), STAR]))]), "xx123xx", ""),

        (Word([VarOp(VarRef(ConstantString("a")), '#', Word([STAR]))]), "xx123xx", "xx123xx"),
        (Word([VarOp(VarRef(ConstantString("a")), '##', Word([STAR]))]), "xx123xx", ""),
        (Word([VarOp(VarRef(ConstantString("a")), '%', Word([STAR]))]), "xx123xx", "xx123xx"),
        (Word([VarOp(VarRef(ConstantString("a")), '%%', Word([STAR]))]), "xx123xx", ""),
))
def test_basic(pattern, value, expected):
    env = make_env()
    env['a'] = value
    result = pattern.evaluate(env)
    assert result == expected


