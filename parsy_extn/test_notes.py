from parsy import whitespace, string, letter, regex, generate, decimal_digit
from . import Noted, get_notes, put_note, keeps_notes


@generate("heredoc")
def heredoc():
    end = yield string("<<") >> word
    hd = HereDoc(end)
    notes = yield get_notes
    hds = notes.get('hds', [])
    hds = list(hds)
    hds.append(hd)
    notes['hds'] = hds
    yield put_note(notes)
    return hd


@generate("eol")
def eol():
    yield string("\n")
    # Do we need to consume some heredocs?
    notes = yield get_notes
    hds = list(notes.get('hds', []))
    while len(hds) > 0:
        hd = hds.pop(0)
        lines = []
        while True:
            l = yield line
            if l == hd.end + "\n":
                break
            lines.append(l)
        hd.content = ''.join(lines)
        notes = dict(notes)
        notes['hds'] = list(hds)
        yield put_note(notes)
    return "\n"


line = regex("[^\n]*\n")
ws = regex("[ \t]+")
word = (letter | decimal_digit).at_least(1).concat()
words = (word | heredoc).sep_by(ws) << eol
words = keeps_notes(words)


class HereDoc:
    def __init__(self, end, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.end = end
        self.content = None

    def __eq__(self, other):
        return self.content == other

    def __repr__(self):
        return "HD({})({!r})".format(self.end, self.content)


def test_note_put_and_get():
    ns = ("a  b  cd <<EOF1 ceh djoqi <<EOF2 odwiqj\n"
          "foo\n"
          "bar\n"
          "EOF1\n"
          "baz\n"
          "EOF2\n")
    ns = Noted.augment(ns)
    assert ns.notes_for(1) == {}
    ns.notes_update(2, {2: 2})
    assert ns._notes == [(2, {2: 2})]
    ns.notes_update(4, {4: 4})
    assert ns._notes == [(2, {2: 2}), (4, {4: 4})]
    ns.notes_update(3, {3: 3})
    assert ns._notes == [(2, {2: 2}), (3, {3: 3})]
    ns.notes_update(3, {3: 4})
    assert ns._notes == [(2, {2: 2}), (3, {3: 4})]
    ns.notes_update(2, {3: 4})
    assert ns._notes == [(2, {3: 4})]


def test_parse_words():
    ns = ("a  b  cd <<EOF1 ceh djoqi <<EOF2 odwiqj\n"
          "foo\n"
          "bar\n"
          "EOF1\n"
          "baz\n"
          "EOF2\n")
    ws = words.parse(ns)
    assert ws == ["a", "b", "cd", "foo\nbar\n", "ceh", "djoqi", "baz\n", "odwiqj"]
