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

if_seq = CommandSequence([
             If([
                 (CommandSequence([
                     Command([Word([Id("a")])]),
                     Command([Word([Id("b")])]),
                  ]),
                  CommandSequence([
                     Command([Word([Id("c")])]),
                     Command([Word([Id("d")])]),
                  ])),
                 (CommandSequence([
                     Command([Word([Id("e")])]),
                     Command([Word([Id("f")])]),
                  ]),
                  CommandSequence([
                     Command([Word([Id("g")])]),
                     Command([Word([Id("h")])]),
                  ])),
                 (If.OTHERWISE,
                  CommandSequence([
                     Command([Word([Id("i")])]),
                     Command([Word([Id("j")])]),
                  ])),
             ]),
         ])


@pytest.mark.parametrize(("text", "expected"), (
        ("cat foo bar\ncat baz",
         CommandSequence([
             Command([Word([Id("cat")]), Word([Id("foo")]), Word([Id("bar")])]),
             Command([Word([Id("cat")]), Word([Id("baz")])]),
         ])),
        ("cat \\\nfoo\\\nbar",
         CommandSequence([
             Command([Word([Id("cat")]), Word([Id("foo"), Id("bar")])]),
         ])),
        ("a; b\nc;\nd",
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
        ("while\n\na\n\nb\n\ndo\n\nc\n\nd\n\ndone\n\n", while_ab_cd),
        ("if  a; b; then  c; d; elif  e; f; then  g; h; else  i; j; fi", if_seq),
        ("if\na; b; then  c; d; elif  e; f; then  g; h; else  i; j; fi", if_seq),
        ("if  a\nb; then  c; d; elif  e; f; then  g; h; else  i; j; fi", if_seq),
        ("if  a; b\nthen  c; d; elif  e; f; then  g; h; else  i; j; fi", if_seq),
        ("if  a; b; then\nc; d; elif  e; f; then  g; h; else  i; j; fi", if_seq),
        ("if  a; b; then  c\nd; elif  e; f; then  g; h; else  i; j; fi", if_seq),
        ("if  a; b; then  c; d\nelif  e; f; then  g; h; else  i; j; fi", if_seq),
        ("if  a; b; then  c; d; elif\ne; f; then  g; h; else  i; j; fi", if_seq),
        ("if  a; b; then  c; d; elif  e\nf; then  g; h; else  i; j; fi", if_seq),
        ("if  a; b; then  c; d; elif  e; f\nthen  g; h; else  i; j; fi", if_seq),
        ("if  a; b; then  c; d; elif  e; f; then\ng; h; else  i; j; fi", if_seq),
        ("if  a; b; then  c; d; elif  e; f; then  g\nh; else  i; j; fi", if_seq),
        ("if  a; b; then  c; d; elif  e; f; then  g; h\nelse  i; j; fi", if_seq),
        ("if  a; b; then  c; d; elif  e; f; then  g; h; else\ni; j; fi", if_seq),
        ("if  a; b; then  c; d; elif  e; f; then  g; h; else  i\nj; fi", if_seq),
        ("if  a; b; then  c; d; elif  e; f; then  g; h; else  i; j\nfi", if_seq),
        ("\n\nif\n\na\n\nb\n\nthen\n\nc\n\nd\n\nelif\n\ne\n\nf\n\nthen\n\ng\n\nh\n\nelse\n\ni\n\nj\n\nfi\n\n", if_seq),
), ids=lambda x: x.replace(" ", "_").replace("\n", "%") if isinstance(x, str) else None)
def test_basic(text, expected):
    cmd = command_sequence.parse(text)
    assert cmd == expected
