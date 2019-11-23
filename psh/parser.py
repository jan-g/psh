from functools import partial
from parsy import eof, regex, generate, string, whitespace, ParseError, fail, seq, success, string_from
from .model import (ConstantString, Token, Id, VarRef, Word, Arith,
                    Command, CommandSequence, CommandPipe, While, If,
                    RedirectFrom, RedirectTo, RedirectDup,
                    MaybeDoubleQuoted)


@generate("command")
def command():
    words = []
    while True:
        yield whitespace.optional()
        w = yield word
        if not w:
            break
        if len(words) == 0 and w.matches_reserved("while", "do", "done", "if", "then", "elif", "else", "fi"):
            return fail("can't have a reserved word here")

        words.append(w)

    cmd = Command(words)
    return cmd


@generate("while")
def command_while():
    yield whitespace.optional()
    redirs1 = yield redirects
    yield whitespace.optional()
    yield string("while")
    cond = yield command_sequence
    yield whitespace.optional() >> string("do")
    body = yield command_sequence
    yield whitespace.optional() >> string("done")
    yield whitespace.optional()
    redirs2 = yield redirects
    yield whitespace.optional()
    return While(condition=cond, body=body).with_redirect(*redirs1, *redirs2)


@generate("cond")
def command_cond():
    yield whitespace.optional()
    redirs1 = yield redirects
    yield whitespace.optional()
    yield string("if")
    cond = yield command_sequence
    yield whitespace.optional() >> string("then")
    body = yield command_sequence
    pairs = [(cond, body)]

    while True:
        tok = yield (whitespace.optional() >> string("elif")).optional()
        if tok is None:
            break
        cond = yield command_sequence
        yield whitespace.optional() >> string("then")
        body = yield command_sequence
        pairs.append((cond, body))

    tok = yield (whitespace.optional() >> string("else")).optional()
    if tok is not None:
        body = yield command_sequence
        pairs.append((If.OTHERWISE, body))

    yield whitespace.optional() >> string("fi")
    yield whitespace.optional()
    redirs2 = yield redirects

    return If(pairs).with_redirect(*redirs1, *redirs2)


compound_command = command_while | command_cond | command


@generate("pipeline")
def pipeline():
    seq = []
    while True:
        cmd = yield compound_command.optional()
        if cmd is not None:
            seq.append(cmd)
        else:
            break
        pipe = yield (regex("[ \t]*") >> string("|")).optional()
        if pipe is None:
            break

    if len(seq) == 1:
        return seq[0]
    return CommandPipe(seq)


@generate("command-sequence")
def command_sequence():
    seq = []
    while True:
        cmd = yield pipeline.optional()
        if cmd is not None:
            seq.append(cmd)
        else:
            break
        semi = yield (regex("[ \t]*") >> string(";")).optional()
        if semi is None:
            break

    return CommandSequence(seq)


variable_id = regex("[a-zA-Z_][a-zA-Z0-9_]*")
variable_name = regex("[0-9\\?!#]") | variable_id
word_id = regex('[^\\s\'()$=";|<>&]+').map(ConstantString)
word_redir = string_from("<&", "<", ">&", ">>", ">").map(Token)
word_single = (string("'") >> regex("[^']*") << string("'")).map(ConstantString)
word_expr = string("$(") >> command_sequence << string(")")
word_variable_reference = (string("$") >> variable_name).map(VarRef)
word_variable_name = variable_id.map(Id)
word_equals = string("=").map(Token)

e_id = variable_id


@generate("expr-simple")
def expr_atom():
    v = yield (whitespace.optional() >> e_id).optional()
    if v is not None:
        return lambda env: float(env.get(v))

    v = yield (whitespace.optional() >> regex(r"-?[0-9]+(\.[0-9]*)?").map(float)).optional()
    if v is not None:
        return lambda env: v

    ex = yield whitespace.optional() >> string("(") >> expr << whitespace.optional() << string(")")
    return ex


@generate("expr-mul")
def expr_mul():
    op = (string("*").result(lambda first: lambda rest: lambda env: first(env) * rest(env)) |
          string("/").result(lambda first: lambda rest: lambda env: first(env) / rest(env)))
    this = lambda _: lambda rest: rest
    ms = yield (success([this]) + expr_atom.times(1)).times(1) + \
               (whitespace.optional() >> op.times(1) + expr_atom.times(1)).many()

    value = None
    for op, item in ms:
        value = op(value)(item)

    return value


@generate("expr-add")
def expr_add():
    op = (string("+").result(lambda first: lambda rest: lambda env: first(env) + rest(env)) |
          string("-").result(lambda first: lambda rest: lambda env: first(env) - rest(env)))
    this = lambda _: lambda rest: rest
    ms = yield (success([this]) + expr_mul.times(1)).times(1) + \
               (whitespace.optional() >> op.times(1) + expr_mul.times(1)).many()

    value = None
    for op, item in ms:
        value = op(value)(item)

    return value


expr = expr_add

word_arith = (string("$((") >> expr << whitespace.optional() << string("))")).map(Arith)

word_double = (string('""').result(Word([ConstantString("")], double_quoted=True))) | \
              (string("\"") >> (regex(r'[^"$\\]+').map(ConstantString) |
                                string(r"\n").result(ConstantString("")) |
                                string(r'\"').result(ConstantString('"')) |
                                string(r"\$").result(ConstantString("$")) |
                                word_arith.map(partial(MaybeDoubleQuoted.with_double_quoted)) |
                                word_variable_reference.map(partial(MaybeDoubleQuoted.with_double_quoted))
                                ).many() << string("\"")).map(lambda rope: Word(rope, double_quoted=True))

word_part = word_variable_reference \
          | word_arith \
          | word_expr \
          | word_variable_name \
          | word_id \
          | word_equals \
          | word_redir \
          | word_single \
          | word_double

word = word_part.many().map(lambda x: x[0] if len(x) == 1 and isinstance(x[0], Word) else Word(x))


redirect_dup_from_n = seq(regex("[0-9]+"), string("<&") >> word).combine(RedirectDup)
redirect_dup_from = (string("<&") >> word).map(partial(RedirectDup, 0))
redirect_from_n = seq(regex("[0-9]+"), string("<") >> word).combine(RedirectFrom)
redirect_from = (string("<") >> word).map(partial(RedirectFrom, 0))
redirect_append_n = seq(regex("[0-9]+"), string(">>") >> word).combine(partial(RedirectTo, append=True))
redirect_append = (string(">>") >> word).map(partial(RedirectTo, 1, append=True))
redirect_dup_to_n = seq(regex("[0-9]+"), string(">&") >> word).combine(RedirectDup)
redirect_dup_to = (string(">&") >> word).map(partial(RedirectDup, 1))
redirect_to_n = seq(regex("[0-9]+"), string(">") >> word).combine(RedirectTo)
redirect_to = (string(">") >> word).map(partial(RedirectTo, 1))

redirect = (redirect_dup_from_n | redirect_dup_from |
            redirect_from_n | redirect_from |
            redirect_append_n | redirect_append |
            redirect_dup_to_n | redirect_dup_to |
            redirect_to_n | redirect_to
            )

redirects = redirect.sep_by(whitespace.optional())


"""
expr_simple = e_id | (string("(") >> expr << string(")"))
expr_add = seq(
    first=expr_simple,
    add=string("+"),
    second = seq(expr_add)
).combine_dict(lambda env: first(env) + second(env))
"""


if __name__ == '__main__':
    c = command.parse("cat   foo bar")
    print(c.words)
