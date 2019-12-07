import pytest

from psh.parser import command_sequence
from psh.model import Word, ConstantString, Command, VarRef, Id, CommandSequence, VarOp


cmd = lambda *ws: CommandSequence([Command([*ws])])
cat = Word([Id("cat")])


@pytest.mark.parametrize(("text", "expected"), (
        ("cat $a", cmd(cat,
                       Word([VarRef(ConstantString("a"))]),
                       )),
        ('cat "$a"', cmd(cat,
                         Word([VarRef(ConstantString("a"), double_quoted=True)], double_quoted=True),
                         )),
        ('cat ${a}', cmd(cat,
                         Word([VarRef(ConstantString("a"))]),
                         )),
        ("cat '$a'", cmd(cat,
                         Word([ConstantString("$a")]),
                         )),
        ("cat '${a}'", cmd(cat,
                           Word([ConstantString("${a}")]),
                           )),
        ('cat "${a}"', cmd(cat,
                           Word([VarRef(ConstantString("a"), double_quoted=True)], double_quoted=True),
                           )),
        ('cat ${a#x}', cmd(cat,
                           Word([VarOp(VarRef(ConstantString("a")), '#', Word([Id("x")]))]),
                           )),
        ('cat ${a##x}', cmd(cat,
                            Word([VarOp(VarRef(ConstantString("a")), '##', Word([Id("x")]))]),
                            )),
        ('cat ${a##"x"}', cmd(cat,
                              Word([VarOp(VarRef(ConstantString("a")), '##', Word([Id("x")], double_quoted=True))]),
                              )),
        ("cat ${a##'x'}", cmd(cat,
                              Word([VarOp(VarRef(ConstantString("a")), '##', Word([Id("x")]))]),
                              )),
        ("cat ${a##\\x}", cmd(cat,
                              Word([VarOp(VarRef(ConstantString("a")), '##', Word([ConstantString("x")]))]),
                              )),
))
def test_basic(text, expected):
    cmd = command_sequence.parse(text)
    assert cmd == expected


