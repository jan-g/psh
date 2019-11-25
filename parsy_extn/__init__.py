import functools
from parsy import Parser, Result


class Noted:
    @staticmethod
    def augment(obj):
        class _(Noted, obj.__class__):
            pass

        _.__name__ = 'Augmented_' + type(obj).__name__

        obj = _(obj)
        obj._notes = []
        return obj

    def notes_for(self, index):
        for idx, n in self._notes[::-1]:
            if idx <= index:
                return dict(n)
        return {}

    def notes_update(self, index, kv):
        for i in range(len(self._notes) - 1, -1, -1):
            idx, n = self._notes[i]
            if idx == index:
                self._notes[i:] = [(index, kv)]
                return
            elif idx < index:
                self._notes[i + 1:] = [(index, kv)]
                return
        self._notes = [(index, kv)]

    def __repr__(self):
        return "{!r}{!r}".format(super(), self._notes)


@Parser
def get_notes(stream, index):
    return Result.success(index, stream.notes_for(index))


def put_note(kv):
    @Parser
    def put_notes(stream, index):
        return Result.success(index, stream.notes_update(index, kv))

    return put_notes


def keeps_notes(parser):
    orig_parse = parser.parse

    def parse_(stream):
        if not isinstance(stream, Noted):
            stream = Noted.augment(stream)
        return orig_parse(stream)

    parser.parse = parse_
    return parser
