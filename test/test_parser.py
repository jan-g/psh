import parsy
import pytest

from psh.parser import command, command_sequence
from psh.model import Word, ConstantString, Assignment, Command, VarRef, Id, Token, CommandSequence, CommandPipe, While, If
from psh.local import make_env


@pytest.mark.parametrize(("text", "expected"), (
        ("cat foo bar", Command([Word([ConstantString("cat")]),
                                 Word([ConstantString("foo")]),
                                 Word([ConstantString("bar")]),
                                 ])),
        ("'hello'", Command([Word([ConstantString("hello")])])),
        ("'hel\nlo'", Command([Word([ConstantString("hel\nlo")])])),
        ("'hello'' world'", Command([Word([ConstantString("hello"),
                                           ConstantString(" world")])])),
        ("$(cat $foo $bar)", Command([Word([CommandSequence([Command([Word([ConstantString("cat")]),
                                                                      Word([VarRef("foo")]),
                                                                      Word([VarRef("bar")])])])])])),
        ("a=2", Command([]).with_assignment(Assignment("a", Word([ConstantString("2")])))),
        ("a=1 b=2 echo $a$b", Command([Word([Id("echo")]),
                                       Word([VarRef("a"), VarRef("b")])]).
         with_assignment(Assignment("a", Word([ConstantString("1")])),
                         Assignment("b", Word([ConstantString("2")])))),
        ("a=2 echo b=1", Command([Word([Id("echo")]),
                                  Word([Id("b"), Token("="), ConstantString("1")])]).
         with_assignment(Assignment("a", Word([ConstantString("2")])))),

))
def test_basic(text, expected):
    cmd = command.parse(text)
    assert cmd == expected
    assert cmd.assignments == expected.assignments
    cmd = command_sequence.parse(text)
    assert cmd == CommandSequence([expected])


@pytest.mark.parametrize(("text", "expected"), (
    ("cat foo bar",
     CommandSequence([Command([Word([ConstantString("cat")]),
                               Word([ConstantString("foo")]),
                               Word([ConstantString("bar")]),
                               ])])),
    ("a; b",
     CommandSequence([Command([Word([Id("a")])]),
                      Command([Word([Id("b")])])])),
    ("a | b",
     CommandSequence([
         CommandPipe([
             Command([Word([Id("a")])]),
             Command([Word([Id("b")])]),
         ])
     ])),
    ("while a; do b; c; done",
     CommandSequence([
         While(
             CommandSequence([
                 Command([Word([Id("a")])]),
             ]),
             CommandSequence([
                 Command([Word([Id("b")])]),
                 Command([Word([Id("c")])]),
             ])
         ),
     ])),
    ("if a; then b; fi",
     CommandSequence([
         If([
             (CommandSequence([
                 Command([Word([Id("a")])]),
             ]),
              CommandSequence([
                  Command([Word([Id("b")])]),
              ])),
         ]),
     ])),
    ("if a; then b; else c; fi",
     CommandSequence([
         If([
             (CommandSequence([
                 Command([Word([Id("a")])]),
             ]),
              CommandSequence([
                  Command([Word([Id("b")])]),
              ])),
             (If.OTHERWISE,
              CommandSequence([
                  Command([Word([Id("c")])]),
              ])),
         ]),
     ])),
    ("if a; then b; elif c; then d; elif e; then f; fi",
     CommandSequence([
         If([
             (CommandSequence([
                 Command([Word([Id("a")])]),
             ]),
              CommandSequence([
                  Command([Word([Id("b")])]),
              ])),
             (CommandSequence([
                 Command([Word([Id("c")])]),
             ]),
              CommandSequence([
                  Command([Word([Id("d")])]),
              ])),
             (CommandSequence([
                 Command([Word([Id("e")])]),
             ]),
              CommandSequence([
                  Command([Word([Id("f")])]),
              ])),
         ]),
     ])),
    ("if a; then b; elif c; then d; elif e; then f; else g; fi",
     CommandSequence([
         If([
             (CommandSequence([
                 Command([Word([Id("a")])]),
             ]),
              CommandSequence([
                  Command([Word([Id("b")])]),
              ])),
             (CommandSequence([
                 Command([Word([Id("c")])]),
             ]),
              CommandSequence([
                  Command([Word([Id("d")])]),
              ])),
             (CommandSequence([
                 Command([Word([Id("e")])]),
             ]),
              CommandSequence([
                  Command([Word([Id("f")])]),
              ])),
             (If.OTHERWISE,
              CommandSequence([
                  Command([Word([Id("g")])]),
              ])),
         ]),
     ])),
))
def test_sequence(text, expected):
    cmd = command_sequence.parse(text)
    assert cmd == expected
    assert cmd.assignments == expected.assignments


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("cat foo bar", 'cat foo bar'.split()),
        ("'hello'", 'hello'.split()),
        ("'hel\nlo'", ['hel\nlo']),
        ("'hello'' world'", ['hello world']),
        ("$foo$bar", ['FOOBAR']),
        ("$foo' '$bar", ['FOO BAR']),
    ))
def test_variables(text, expected):
    env = make_env()
    env.update({"foo": "FOO", "bar": "BAR"})
    cmd = command.parse(text)
    words = [item.evaluate(env) for item in cmd]
    assert words == expected


def test_not_yet():
    with pytest.raises(parsy.ParseError):
        command.parse("$(cat foo")


def test_while():
    with pytest.raises(parsy.ParseError):
        assert command.parse("while") is None
