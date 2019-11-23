import parsy
import pytest

from psh.parser import command, command_sequence
from psh.model import Word, ConstantString, Command, VarRef, Id, Token, CommandSequence, CommandPipe, While, If
from psh.builtin import Env, make_env


while_ab_cd = CommandSequence([
                 While(
                     CommandSequence([
                         Command([Word([Id("a")])]),
                         Command([Word([Id("b")])]),
                     ]),
                     CommandSequence([
                         Command([Word([Id("c")])]),
                         Command([Word([Id("d")])]),
                     ])
                 ),
             ])

@pytest.mark.parametrize(("text", "expected"), (
        ("cat foo bar\ncat baz",
         CommandSequence([
             Command([Word([Id("cat")]), Word([Id("foo")]), Word([Id("bar")])]),
             Command([Word([Id("cat")]), Word([Id("baz")])]),
         ])),
        ("a; b\nc; d",
         CommandSequence([
             Command([Word([Id("a")])]),
             Command([Word([Id("b")])]),
             Command([Word([Id("c")])]),
             Command([Word([Id("d")])]),
         ])),
        ("a |\n b",
         CommandSequence([
             CommandPipe([
                 Command([Word([Id("a")])]),
                 Command([Word([Id("b")])]),
             ]),
         ])),
        ("while a; b; do  c; d; done", while_ab_cd),
        ("while a\nb; do  c; d; done", while_ab_cd),
        ("while a; b\ndo  c; d; done", while_ab_cd),
        ("while a; b; do\nc; d; done", while_ab_cd),
        ("while a; b; do  c\nd; done", while_ab_cd),
        ("while a; b; do  c; d\ndone", while_ab_cd),
), ids=lambda x: x.replace(" ", "_").replace("\n", "%") if isinstance(x, str) else None)
def test_basic(text, expected):
    cmd = command_sequence.parse(text)
    assert cmd == expected


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
