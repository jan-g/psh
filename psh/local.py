from .model import While, Function, Break, Continue
from .builtin import Env


def echo(*args, env=None, stdin=None, stdout=None, stderr=None):
    stdout.write(bytes(" ".join(args) + "\n", "utf-8"))
    stdout.flush()
    return 0


def local(*args, env=None, stdin=None, stdout=None, stderr=None):
    for a in args:
        kv = a.split("=", 2)
        if len(kv) == 1:
            env.variables[kv[0]] = env.get(kv[0])
        else:
            env.variables[kv[0]] = kv[1]


def break_(*args, env=None, stdin=None, stdout=None, stderr=None):
    if len(args) == 0:
        n = 1
    elif len(args) == 1:
        n = int(args[0])
    else:
        raise Exception("duff break - we need some exception handling strategy here")
    raise Break(n)


def continue_(*args, env=None, stdin=None, stdout=None, stderr=None):
    if len(args) == 0:
        n = 1
    elif len(args) == 1:
        n = int(args[0])
    else:
        raise Exception("duff continue - we need some exception handling strategy here")
    raise Continue(n)


def return_(*args, env=None, stdin=None, stdout=None, stderr=None):
    if len(args) == 0:
        n = int(env.get('?', 0))
    elif len(args) == 1:
        n = int(args[0])
    else:
        raise Exception("duff return - we need some exception handling strategy here")
    raise Function.Return(n)


def colon(*args, env=None, stdin=None, stdout=None, stderr=None):
    return 0


def make_env():
    env = Env()
    env.permit_execution = True
    env.builtins = {
        "echo": echo,
        "local": local,
        "break": break_,
        "continue": continue_,
        "return": return_,
        ":": colon,
    }
    return env
