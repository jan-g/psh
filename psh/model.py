import io
import os
import subprocess
import sys


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


class Token(ConstantString):
    pass


class Id(ConstantString):
    pass


class VarRef(str):
    def evaluate(self, env):
        return env[str(self)]


ASSIGN = Token("=")


class Evaluable:
    def evaluate(self, env, input=None, output=None, error=None):
        out = io.BytesIO()
        self.execute(env, input=input, output=out, error=error)
        return out.getvalue().decode("utf-8").rstrip("\n")

    def execute(self,  env, input=None, output=None, error=None):
        raise NotImplementedError()


class List(list, Evaluable):
    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, list(self))


class Command(List):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Extract assignments and redirects
        self.redirects = []
        self.assignments = []
        items = []
        might_be_assignment = True

        for item in self:
            if might_be_assignment and isinstance(item, Word) and item.matches_assignment():
                self.assignments.append(item)
                continue
            might_be_assignment = False
            items.append(item)

        self[:] = items

    def execute(self, env, input=None, output=None, error=None):
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
        self[:] = [item for item in self if not (isinstance(item, list) and len(item) == 0)]

    def execute(self, env, input=None, output=None, error=None):
        assert env.permit_execution

        r = 0
        for item in self:
            r = item.execute(env, input=input, output=output, error=error)

        return r


class CommandPipe(List):
    """A sequence of Command objects. We create pipes between each."""

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


class While(Evaluable):
    def __init__(self, condition=None, body=None):
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


class If(List):
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
