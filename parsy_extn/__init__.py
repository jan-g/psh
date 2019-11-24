from parsy import Parser, Result


class NotedString(str):
    def __init__(self, s, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._notes = []

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

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "{}{!r}".format(super(), self._notes)


@Parser
def get_notes(stream, index):
    return Result.success(index, stream.notes_for(index))
    match = exp.match(stream, index)
    if match:
        return Result.success(match.end(), match.group(0))
    else:
        return Result.failure(index, exp.pattern)


def put_note(kv):
    @Parser
    def put_notes(stream, index):
        return Result.success(index, stream.notes_update(index, kv))

    return put_notes
