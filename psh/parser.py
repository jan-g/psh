from functools import partial
from parsy import eof, regex, generate, string, ParseError, fail, seq, success, string_from, eof, any_char
from parsy_extn import monkeypatch_parsy, get_notes, put_note

from .model import (ConstantString, Token, Id, VarRef, Word, Arith, Assignment,
                    Command, CommandSequence, CommandPipe, While, If, Function,
                    Redirect, RedirectFrom, RedirectTo, RedirectDup, RedirectHere,
                    MaybeDoubleQuoted, VarOp)
from .glob import STAR, STARSTAR


# All our parser use may need to carry notes forward.
# This cost is only paid if we actually muck around with heredocs.
monkeypatch_parsy()


ws = regex('([ \t]|\\\\\n)+')


@generate("eol")
def eol():
    """ Parse and consume a single '\n' character.

    If there are any heredocs pending, immediately consume more lines of input
    until all heredocs are filled in.
    """
    yield string("\n")

    # Do we need to consume some heredocs?
    notes = yield get_notes

    # make a copy of this list so that we don't perturb the note.
    hds = list(notes.get('hds', []))

    while len(hds) > 0:
        # The next heredoc to scan for
        hd = hds.pop(0)

        lines = []
        while True:
            line = yield eof.result(EOF) | regex("[^\n]*\n") | regex("[^\n]*") << eof
            if line is EOF:
                return fail("looking for heredoc ending with " + hd.end)
            if line.rstrip("\n") == hd.end:
                break
            lines.append(line)

        content = '\n'.join(lines)

        if content == '':
            content = ConstantString("")
        elif hd.quote is None:
            content = double_content.parse(content)
        else:
            content = ConstantString(content)

        # Back-fill the HereDoc content. Note, this is *not* undone by backtracking.
        # However, a backtrack and re-parse may overwrite this value; so in the end,
        # it's likely that this will do what we want.
        hd.file = content

        # `notes` itself is a shallow copy, so we don't need to worry about copying it here.
        notes['hds'] = hds
        yield put_note(notes)
    return "\n"


whitespace = ws | eol


# End of statement
EOF = object()
EOS = object()
eos = ws.optional() >> (string(";") | eol | eof.result(EOF))


@generate("command")
def command():
    words = []
    assignments = []
    redirs = []
    assignments_possible = True
    while True:
        yield ws.optional()
        if assignments_possible:
            w = yield assignment | redirect | word
        else:
            w = yield redirect | word
        if isinstance(w, Word):
            assignments_possible = False
        elif isinstance(w, Redirect):
            redirs.append(w)
            continue
        elif isinstance(w, Assignment):
            assignments.append(w)
            continue

        if not w:
            break
        if len(words) == 0 and w.matches_reserved("while", "do", "done", "if", "then", "elif", "else", "fi"):
            return fail("can't have a reserved word here")

        words.append(w)

    cmd = Command(words).with_assignment(*assignments).with_redirect(*redirs)
    return cmd


@generate("while")
def command_while():
    yield ws.optional()
    redirs1 = yield redirects
    yield ws.optional()
    yield string("while")
    cond = yield command_sequence
    yield whitespace.optional() >> string("do") << ws.optional() << eol.optional()
    body = yield command_sequence
    yield whitespace.optional() >> string("done")
    yield ws.optional()
    redirs2 = yield redirects
    return While(condition=cond, body=CommandSequence(body)).with_redirect(*redirs1, *redirs2)


@generate("cond")
def command_cond():
    yield ws.optional()
    redirs1 = yield redirects
    yield ws.optional()
    yield string("if")
    cond = yield command_sequence
    yield whitespace.optional() >> string("then") << ws.optional() << eol.optional()
    body = yield command_sequence
    pairs = [(cond, body)]

    while True:
        tok = yield (whitespace.optional() >> string("elif")).optional() << ws.optional() << eol.optional()
        if tok is None:
            break
        cond = yield command_sequence
        yield whitespace.optional() >> string("then") << ws.optional() << eol.optional()
        body = yield command_sequence
        pairs.append((cond, body))

    tok = yield (whitespace.optional() >> string("else")).optional() << ws.optional() << eol.optional()
    if tok is not None:
        body = yield command_sequence
        pairs.append((If.OTHERWISE, body))

    yield whitespace.optional() >> string("fi")
    yield ws.optional()
    redirs2 = yield redirects

    return If(pairs).with_redirect(*redirs1, *redirs2)


@generate("command-brackets")
def command_brackets():
    yield ws.optional() >> string("{")
    cmd = yield command_sequence
    yield string("}")
    return cmd


@generate("function")
def function_def():
    name = yield word_id << ws.optional()
    yield string("()") << ws.optional()
    body = yield command_brackets
    return Function(name, body)


compound_command = function_def | command_brackets | command_while | command_cond | command


@generate("pipeline")
def pipeline():
    seq = []
    while True:
        cmd = yield ws.optional() >> eol.optional() >> compound_command.optional()
        if cmd is not None:
            if not cmd.is_null():
                seq.append(cmd)
        else:
            break
        pipe = yield (ws.optional() >> string("|")).optional()
        if pipe is None:
            break

    if len(seq) == 1:
        return seq[0]
    return CommandPipe(seq)


@generate("command-sequence")
def command_sequence():
    seq = []
    while True:
        cmd = yield pipeline
        if cmd is not None:
            seq.append(cmd)
        else:
            break
        semi = yield (ws.optional() >> eos).optional()
        if semi is None:
            break
        if semi is EOF:
            break

    notes = yield get_notes

    # make a copy of this list so that we don't perturb the note.
    hds = list(notes.get('hds', []))
    if len(hds) > 0:
        return fail("Want additional heredocs")

    return CommandSequence(seq)


eaten_newline = string("\\\n").result(Token(""))
variable_id = regex("[a-zA-Z_][a-zA-Z0-9_]*")
variable_name = regex("[1-9][0-9]*|[0\\?!#@\\*]") | variable_id
word_id = regex('[^\\s\'()$=";|<>&\\\\{}`*]+').map(ConstantString)
word_redir = string_from("<&", "<<", "<", ">&", ">>", ">").map(Token)
word_single = (string("'") >> regex("[^']*") << string("'")).map(ConstantString)
word_expr = string("$(") >> command_sequence << string(")")
word_backslash = string("\\") >> any_char.map(ConstantString)
word_variable_reference = (string("$") >> variable_name).map(ConstantString).map(VarRef)
word_variable_name = variable_id.map(Id)
word_equals = string("=").map(Token)
word_dbrace = string("{}").map(Token)
word_glob = string("**").result(STARSTAR) | string("*").result(STAR)

e_id = variable_id


@generate("word-variable-complex")
def word_variable_complex():
    yield string("${")
    ref = yield variable_name.map(ConstantString).map(VarRef)
    op = yield string_from("##", "#", "%%", "%").optional()
    if op is not None:
        param = yield word
        ref = VarOp(ref, op, param)
    yield string("}")
    return ref


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

# This is also used for the expansion of heredocs that don't have quotes around the end token.
double_content = (regex(r'[^"$\\]+').map(ConstantString) |
                  string("\\\n").result(ConstantString("")) |
                  string("\\n").result(ConstantString("\n")) |
                  string("\\t").result(ConstantString("\t")) |
                  string("\\b").result(ConstantString("\b")) |
                  string("\\") >> any_char.map(ConstantString) |
                  word_arith.map(partial(MaybeDoubleQuoted.with_double_quoted)) |
                  word_expr.map(partial(MaybeDoubleQuoted.with_double_quoted)) |
                  word_variable_reference.map(partial(MaybeDoubleQuoted.with_double_quoted)) |
                  word_variable_complex.map(partial(MaybeDoubleQuoted.with_double_quoted))
                  ).many().map(lambda rope: Word(rope, double_quoted=True))

word_double = (string('""').result(Word([ConstantString("")], double_quoted=True))) | \
              (string("\"") >> double_content << string("\""))


@generate("backtick")
def backtick():
    """ Parse backticks. This is fugly.

    Backticks: I gave up on single-pass parsing here. It would be doable with the 'notes' extension, but would require
    enough context carrying forward that it'd need reimplementations of all bare string- and regex-matching things to
    understand how many levels deep they are.

    Here is the skinny: the shell has the $( ) which offer an objectively cleaner syntax.
    We parse backticks recursively because it's about the neatest approach to implement the shell spec that describes
    the feature in terms of a recursive implementation.

    The Posix shell spec, section 2.6.3, says this:

        Within the backquoted style of command substitution, <backslash> shall retain its literal meaning, except when
        followed by: '$', '`', or <backslash>. The search for the matching backquote shall be satisfied by the first
        unquoted non-escaped backquote; during this search, if a non-escaped backquote is encountered within a shell
        comment, a here-document, an embedded command substitution of the $(command) form, or a quoted string,
        undefined results occur. A single-quoted or double-quoted string that begins, but does not end, within the
        "`...`" sequence produces undefined results.

    What a mess.
    """
    content = yield string("`") >> (string("`").should_fail("backtick") >> (
                                    string(r"\`").result("`") |
                                    string(r"\$").result("$") |
                                    string(r"\\").result("\\") |
                                    regex(r'[^\\`]*') |
                                    string("\\")
                                    )).many().concat() << string("`")
    return command_sequence.parse(content)


word_part = backtick \
          | word_variable_reference \
          | word_arith \
          | word_expr \
          | word_variable_name \
          | word_variable_complex \
          | word_id \
          | word_equals \
          | word_redir \
          | word_single \
          | word_double \
          | word_dbrace \
          | eaten_newline \
          | word_backslash \
          | word_glob

word = word_part.many().map(
    lambda x: x[0] if len(x) == 1 and isinstance(x[0], Word) else
    Word([i for i in x if i != Token("")]))

assignment = seq(variable_id, string("="), word).map(lambda vew: Assignment(vew[0], vew[2]))

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


@generate("redirect-heredoc")
def redirect_heredoc():
    yield string("<<")
    quote = yield (string('"') | string("'")).optional()
    tag = yield word_id
    if quote is not None:
        yield string(quote)

    hd = RedirectHere(0, quote=quote, end=str(tag))

    # We keep track of the list of heredocs we are looking for, in order.
    notes = yield get_notes
    # We have to take care to copy the previous notes' list; we don't want to
    # mutate the list itself during parsing and backtracking.
    notes['hds'] = list(notes.get('hds', [])) + [hd]
    yield put_note(notes)

    return hd


redirect = (redirect_heredoc |
            redirect_dup_from_n | redirect_dup_from |
            redirect_from_n | redirect_from |
            redirect_append_n | redirect_append |
            redirect_dup_to_n | redirect_dup_to |
            redirect_to_n | redirect_to
            )

redirects = redirect.sep_by(ws.optional())


if __name__ == '__main__':
    c = command.parse("cat   foo bar")
    print(c.words)
