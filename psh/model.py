import io
import os
import re
import subprocess


class Word(list):
    """ A Word is comprised of several parts"""
    def evaluate(self, env):
        return ''.join(item.evaluate(env) for item in self)

    def matches_assignment(self):
        return len(self) >= 2 and isinstance(self[0], Id) and Token("=") == self[1]

    def matches_reserved(self, *reserved):
        if len(self) == 1 and isinstance(self[0], ConstantString) and str(self[0]) in reserved:
            return str(self[0])
        return None

    def matches_redirect(self):
        """ Match for a redirect

            n>file
            n<file
            n>>file
            n>&m
            n<&m
            n>-
            n<-

            (Later)
            <<<Word
        """
        types = [type(item) for item in self]
        print(types)
        if types == [ConstantString, Token, ConstantString] and self[0].is_number() and self[1] == "<":
            return RedirectFrom(self[0], self[2])
        return None

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.__class__(super().__getitem__(key))
        else:
            return super().__getitem__(key)


class ConstantString(str):
    """ An uninterpreted piece of string """
    def evaluate(self, env):
        return str(self)

    def __eq__(self, other):
        return (isinstance(other, type(self)) or isinstance(self, type(other))) and str(self) == str(other)

    NUMBER = re.compile("[0-9]+")
    def is_number(self):
        return self.NUMBER.match(self)


class Token(ConstantString):
    pass


class Id(ConstantString):
    pass


class VarRef(str):
    def evaluate(self, env):
        return env[str(self)]


ASSIGN = Token("=")


class Redirect:
    def __init__(self, fd, file, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fd = fd
        self.file = file

    def do(self, env):
        raise NotImplementedError

    def __eq__(self, other):
        return type(self) == type(other) and self.fd == other.fd and self.file == other.file


class RedirectFrom(Redirect):
    def __init__(self, fd, file, *args, **kwargs):
        super().__init__(int(fd), file, *args, **kwargs)

    def do(self, env):
        os.close(self.fd)
        f = self.file.evaluate(env)
        fd = os.open(self.file, "rb")
        if fd != self.fd:
            os.dup2(fd, self.fd)
            os.close(fd)


class Evaluable:
    def evaluate(self, env, input=None, output=None, error=None):
        out = io.BytesIO()
        self.execute(env, input=input, output=out, error=error)
        return out.getvalue().decode("utf-8").rstrip("\n")

    def execute(self,  env, input=None, output=None, error=None):
        raise NotImplementedError()

    def is_null(self):
        return False


class Redirects:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redirects = []

    def with_redirect(self, redirect):
        self.redirects.append(redirect)
        return self


class Arith(Evaluable):
    def __init__(self, expr, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.expr = expr

    def execute(self,  env, input=None, output=None, error=None):
        raise RuntimeError("don't try to execute arithmetic expressions")

    def evaluate(self, env, input=None, output=None, error=None):
        return str(self.expr(env))


class List(Evaluable, list):
    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, list(self))


class Command(Redirects, List):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Extract assignments and redirects
        self.assignments = []
        items = []
        might_be_assignment = True

        for item in self:
            if isinstance(item, Word):
                if might_be_assignment and item.matches_assignment():
                    self.with_assignment(item)
                    continue
                might_be_assignment = False

                redir = item.matches_redirect()
                if redir is not None:
                    self.with_redirect(redir)
                    continue

            items.append(item)

        self[:] = items

    def with_assignment(self, assignment):
        self.assignments.append(assignment)
        return self

    def is_null(self):
        return len(self) == len(self.redirects) == len(self.assignments) == 0

    def execute(self, env, input=None, output=None, error=None):
        print("executing:", self)
        assert env.permit_execution
        for var, _, *rest in self.assignments:
            assert isinstance(var, Id)
            env[str(var)] = Word(rest).evaluate(env)
        if env.permit_execution and len(self) > 0:
            args = [item.evaluate(env) for item in self]
            if args[0] in env.builtins:
                res = env.builtins[args[0]](*args[1:], env=env,
                                            stdin=input,
                                            stdout=output,
                                            stderr=error)
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
                                 preexec_fn=None,
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
        self[:] = [item for item in self if not (isinstance(item, list) and item.is_null())]

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
    def __init__(self, condition=None, body=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.condition = condition
        self.body = body

    def execute(self, env, input=None, output=None, error=None):
        while True:
            res = self.condition.execute(env, input=input, output=output, error=error)
            if res != 0:
                return res
            self.body.execute(env, input=input, output=output, error=error)

    def __repr__(self):
        return "While({}, {})".format(self.condition, self.body)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.condition == other.condition and self.body == other.body


class If(List, Redirects):
    OTHERWISE = object()

    def execute(self,  env, input=None, output=None, error=None):
        res = 0
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
