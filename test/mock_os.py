import contextlib
import fcntl
import os
from _pytest.monkeypatch import MonkeyPatch


class Os:
    STDIN = ("STDIN", "r")
    STDOUT = ("STDOUT", "w")
    STDERR = ("STDERR", "w")

    def __init__(self, fds=None):
        if fds is None:
            fds = {0: Os.STDIN, 1: Os.STDOUT, 2: Os.STDERR}

        self.fds = fds

    def open(self, file, mode):
        fd = self._free()
        self.fds[fd] = (file, mode)
        return fd

    def close(self, fd):
        try:
            del self.fds[fd]
        except KeyError:
            raise OSError()

    def dup(self, fd):
        try:
            data = self.fds[fd]
            fd2 = self._free()
            self.fds[fd2] = data
            return fd2
        except KeyError:
            raise OSError()

    def dup2(self, fd, fd2):
        try:
            self.fds[fd2] = self.fds[fd]
            return fd2
        except KeyError:
            raise OSError()

    def fcntl(self, fd, cmd, arg):
        assert cmd == fcntl.F_DUPFD
        for i in range(arg, 1023):
            if i not in self.fds:
                try:
                    self.fds[i] = self.fds[fd]
                    return i
                except KeyError:
                    raise OSError()

    def _free(self):
        for i in range(1023):
            if i not in self.fds:
                return i

    @contextlib.contextmanager
    def patch(self):
        with MonkeyPatch().context() as mp:
            mp.setattr(os, "open", self.open)
            mp.setattr(os, "close", self.close)
            mp.setattr(os, "dup", self.dup)
            mp.setattr(os, "dup2", self.dup2)
            mp.setattr(fcntl, "fcntl", self.fcntl)
            yield


def test_os():
    o = Os()
    with o.patch():
        assert os.open("blah", os.O_RDONLY) == 3
        assert o.fds[3] == ("blah", os.O_RDONLY)
        assert os.dup2(3, 1) == 1
    assert o.fds[1] == ("blah", os.O_RDONLY)
