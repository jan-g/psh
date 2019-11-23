class Env(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.permit_execution = False
        self.builtins = {}
        self.functions = {}


def echo(*args, env=None, stdin=None, stdout=None, stderr=None):
    stdout.write(bytes(" ".join(args) + "\n", "utf-8"))
    stdout.flush()
    return 0


def make_env():
    env = Env()
    env.permit_execution = True
    env.builtins = {
        "echo": echo,
    }
    return env
