import attr
import contextlib
import fcntl
import io
import logging
import os
import re
import subprocess

from .builtin import Env

LOG = logging.getLogger(__name__)


class Comparable:
    def __eq__(self, other):
        return ((isinstance(other, type(self))
                 and all(other.__dict__.get(k) == v
                         for (k, v) in self.__dict__.items()
                         if not k.startswith("_"))) or
                (isinstance(self, type(other))
                 and all(self.__dict__.get(k) == v
                         for (k, v) in other.__dict__.items()
                         if not k.startswith("_"))))


class Evaluable:
    def evaluate(self, env, input=None, output=None, error=None):
        out = io.BytesIO()
        self.execute(env, input=input, output=out, error=error)
        return out.getvalue().decode("utf-8").rstrip("\n")

    def execute(self,  env, input=None, output=None, error=None):
        raise NotImplementedError()

    def is_null(self):
        return False


class List(Comparable, Evaluable):
    def __init__(self, items, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items = items

    def __repr__(self):
        return "{}({!r}{})".format(self.__class__.__name__, self.items,
                                   "".join(", {}={!r}".format(k, v)
                                           for (k, v) in self.__dict__.items()
                                           if not k.startswith("_")
                                           and k != "items"))

    def execute(self,  env, input=None, output=None, error=None):
        raise NotImplementedError()

    def __getitem__(self, key):
        return self.items[key]

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            self.items[key] = list(value)
        else:
            self.items[key] = value

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def append(self, item):
        return self.items.append(item)

    def extend(self, items):
        return self.items.extend(items)

    def __eq__(self, other):
        return (isinstance(other, list) and self.items == other) or super().__eq__(other)


class MaybeDoubleQuoted:
    def __init__(self, *args, double_quoted=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.double_quoted = double_quoted

    def with_double_quoted(self, double_quoted=True):
        self.double_quoted = double_quoted
        return self


class Word(MaybeDoubleQuoted, List):
    """ A Word is comprised of several parts"""
    def evaluate(self, env, input=None, output=None, error=None):
        return ''.join(item.evaluate(env) for item in self)

    def matches_reserved(self, *reserved):
        if len(self) == 1 and isinstance(self[0], ConstantString) and str(self[0]) in reserved:
            return str(self[0])
        return None

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.__class__(super().__getitem__(key))
        else:
            return super().__getitem__(key)


@attr.s
class Assignment:
    var = attr.ib()
    expr = attr.ib()

    @staticmethod
    def run(env, assignments):
        for a in assignments:
            assert isinstance(a.var, str)
            env[str(a.var)] = a.expr.evaluate(env)


class ConstantString(Comparable):
    """ An uninterpreted piece of string """
    def __init__(self, s, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.s = str(s)

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.s)

    def __str__(self):
        return self.s

    def __int__(self):
        return int(self.s)

    def __float__(self):
        return float(self.s)

    def evaluate(self, env):
        return self.s

    def __eq__(self, other):
        return (isinstance(other, str) and self.s == other) or super().__eq__(other)


class Token(ConstantString):
    pass


class Id(ConstantString):
    pass


class VarRef(Comparable, MaybeDoubleQuoted):
    def __init__(self, expr=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.expr = expr

    def evaluate(self, env):
        return env[str(self.expr)]

    def __repr__(self):
        quote = '"' if self.double_quoted else ''
        return '{0}${{{1}}}{0}'.format(quote, self.expr)


ASSIGN = Token("=")


class Redirect:
    def __init__(self, fd, file, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fd = int(fd)
        self.file = file

    @staticmethod
    @contextlib.contextmanager
    def activate(env, redirects):
        saver = Redirect.Saver()
        redirects.run_redirects(env, saver=saver)
        try:
            yield saver
        finally:
            saver.restore()

    class Saver:
        def __init__(self):
            self.saved = set()
            self.was = {}
            self.max = 100

        def move(self, target):
            self.max = max(self.max, target + 1)
            if target not in self.saved:
                # Move it.
                try:
                    self.was[fcntl.fcntl(target, fcntl.F_DUPFD, self.max)] = target
                    self.saved.add(target)
                except OSError:
                    pass
                return
            else:
                pass

        def restore(self):
            for now_at in self.was:
                os.dup2(now_at, self.was[now_at])
                if now_at not in self.saved:
                    os.close(now_at)

    class NullSaver:
        def move(self, target):
            pass

    NULL_SAVER = NullSaver()

    def do(self, env):
        raise NotImplementedError

    def __eq__(self, other):
        return type(self) == type(other) and self.fd == other.fd and self.file == other.file

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__,
                               ", ".join("{}={}".format(k, v)
                                         for (k, v) in self.__dict__.items()
                                         if not k.startswith("_")))


class RedirectFrom(Redirect):
    def do(self, env, saver=Redirect.NULL_SAVER):
        saver.move(self.fd)
        os.close(self.fd)
        fn = self.file.evaluate(env)
        fd = os.open(fn, os.O_RDONLY)
        if fd != self.fd:
            os.dup2(fd, self.fd)
            os.close(fd)


class RedirectTo(Redirect):
    def __init__(self, fd, file, append=False, *args, **kwargs):
        super().__init__(int(fd), file, *args, **kwargs)
        self.append = append

    def do(self, env, saver=Redirect.NULL_SAVER):
        fn = self.file.evaluate(env)
        fd = os.open(fn, os.O_WRONLY | os.O_TRUNC | os.O_CREAT | (os.O_APPEND if self.append else 0))
        if fd != self.fd:
            saver.move(self.fd)
            os.dup2(fd, self.fd)
            os.close(fd)
        else:
            os.set_inheritable(fd, True)


class RedirectDup(Redirect):
    def do(self, env, saver=Redirect.NULL_SAVER):
        fd = self.file.evaluate(env)
        saver.move(self.fd)
        if fd == "-":
            try:
                os.close(self.fd)
            except OSError:
                pass
        else:
            fd = int(fd)
            if fd != self.fd:
                os.dup2(fd, self.fd)


class RedirectHere(Redirect):
    def __init__(self, fd=0, quote=None, end=None, content=None, *args, **kwargs):
        super().__init__(fd, content, *args, **kwargs)
        self.quote = quote
        self.end = end

    def do(self, env, saver=Redirect.NULL_SAVER):
        value = self.file.evaluate(env)

        rd, wr = os.pipe()
        child = os.fork()
        if child == 0:
            # Child process.
            os.close(rd)
            try:
                os.write(wr, bytes(value, "utf-8"))
                res = 0
            except OSError as e:
                res = e.errno
            os._exit(res)
        else:
            # Parent process
            os.close(wr)
            if rd != self.fd:
                saver.move(self.fd)
                os.dup2(rd, self.fd)
                os.close(rd)
            else:
                os.set_inheritable(rd, True)


class Redirects:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redirects = []

    def with_redirect(self, *redirect):
        self.redirects.extend(redirect)
        return self

    def run_redirects(self, env, saver=Redirect.NULL_SAVER):
        for redirect in self.redirects:
            redirect.do(env, saver=saver)


class Arith(MaybeDoubleQuoted, Evaluable):
    def __init__(self, expr, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.expr = expr

    def execute(self,  env, input=None, output=None, error=None):
        raise RuntimeError("don't try to execute arithmetic expressions")

    def evaluate(self, env, input=None, output=None, error=None):
        return str(self.expr(env))


class Command(Redirects, List):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Extract assignments and redirects
        self.assignments = []

    def with_assignment(self, *assignment):
        self.assignments.extend(assignment)
        return self

    def is_null(self):
        return len(self) == len(self.redirects) == len(self.assignments) == 0

    def execute(self, env, input=None, output=None, error=None):
        LOG.debug("executing: %s", self)
        assert env.permit_execution
        Assignment.run(env, self.assignments)
        if env.permit_execution and len(self) > 0:
            args = [item.evaluate(env) for item in self]
            if args[0] in env.builtins:
                with Redirect.activate(env, self) as saver:
                    res = env.builtins[args[0]](*args[1:], env=env,
                                                stdin=input,
                                                stdout=output,
                                                stderr=error)
                env['?'] = str(res)
                return res

            if args[0] in env.functions:
                with Redirect.activate(env, self) as saver:
                    res = env.functions[args[0]].call(*args[1:], env=env,
                                                      input=input,
                                                      output=output,
                                                      error=error)
                    env['?'] = str(res)
                    return res

            try:
                if output is not None:
                    output.fileno()
                out = output
            except io.UnsupportedOperation:
                out = subprocess.PIPE
            try:
                if error is not None:
                    error.fileno()
                err = error
            except io.UnsupportedOperation:
                err = subprocess.PIPE
            p = subprocess.Popen(args, bufsize=0, executable=None,
                                 stdin=input, stdout=out, stderr=err,
                                 preexec_fn=lambda: self.run_redirects(env),
                                 close_fds=False,
                                 cwd=None,
                                 env=None)
            o, e = p.communicate()
            res = p.returncode
            if out is subprocess.PIPE:
                output.write(o)
            if err is subprocess.PIPE:
                error.write(e)
            env['?'] = str(res)
            return res


class CommandSequence(Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self[:] = [item for item in self if not (isinstance(item, List) and item.is_null())]

    def execute(self, env, input=None, output=None, error=None):
        assert env.permit_execution

        r = 0
        for item in self:
            r = item.execute(env, input=input, output=output, error=error)

        return r


class CommandPipe(List):
    """A sequence of Command objects. We create pipes between each."""

    def is_null(self):
        return len(self) == 0

    def execute(self, env, input=None, output=None, error=None):
        if len(self) == 0:
            return 0

        pids = []
        for item in self[:-1]:
            # Open a pipe for output
            rd, wr = os.pipe()
            child = os.fork()
            if child == 0:
                # Child process.
                os.close(rd)
                res = item.execute(env, input=input, output=io.open(wr, "wb"), error=error)
                os._exit(res)
            else:
                # Parent process
                pids.append(child)
                os.close(wr)
                input = io.open(rd, "rb")

        item = self[-1]
        res = item.execute(env, input=input, output=output, error=error)

        if len(self) > 1:
            try:
                input.close()
            except IOError as e:
                pass

        for pid in pids:
            os.waitpid(pid, 0)

        return res


class While(Evaluable, Redirects):
    class Break(Exception):
        def __init__(self, n, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.n = n

    def __init__(self, condition=None, body=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.condition = condition
        self.body = body

    def execute(self, env, input=None, output=None, error=None):
        with Redirect.activate(env, self) as saver:
            while True:
                res = self.condition.execute(env, input=input, output=output, error=error)
                if res != 0:
                    return res
                try:
                    self.body.execute(env, input=input, output=output, error=error)
                except While.Break as e:
                    e.n -= 1
                    if e.n <= 0:
                        return 0
                    raise e

    def __repr__(self):
        return "While({}, {})".format(self.condition, self.body)

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self.condition == other.condition and
                self.body == other.body and
                self.redirects == other.redirects)


class If(Redirects, List):
    OTHERWISE = object()

    def execute(self, env, input=None, output=None, error=None):
        res = 0

        with Redirect.activate(env, self) as saver:
            for cond, body in self:
                if cond is If.OTHERWISE:
                    test = True
                else:
                    res = cond.execute(env, input=input, output=output, error=error)
                    test = res == 0
                if test:
                    res = body.execute(env, input=input, output=output, error=error)
                    break

        return res

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                list(self) == list(other) and
                self.redirects == other.redirects)


class Function(Comparable, Evaluable):
    class Return(Exception):
        def __init__(self, ret, *args, **kwargs):
            self.ret = ret

    def __init__(self, name, body, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.body = body

    def is_null(self):
        return False

    def execute(self, env, input=None, output=None, error=None):
        env.functions[self.name] = self.body

    def __repr__(self):
        return "{}({}={!r})".format(self.__class__.__name__, self.name, self.body)

    def call(self, *args, env=None, input=None, output=None, error=None):
        local = {}
        for i, v in enumerate(args):
            local[str(i+1)] = v
        local['#'] = str(len(args))
        env2 = Env(variables=local, parent=env)

        try:
            return self.body.execute(env2, input=input, output=output, error=error)
        except Function.Return as e:
            return e.ret
