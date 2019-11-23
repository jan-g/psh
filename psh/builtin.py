class Env:
    def __init__(self, variables=None, parent=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if variables is None:
            variables = {}
        self.variables = variables
        self.parent = parent
        self.permit_execution = False if parent is None else parent.permit_execution
        self.builtins = {} if parent is None else parent.builtins
        self.functions = {} if parent is None else parent.functions

    def __getitem__(self, key):
        if key in self.variables:
            return self.variables[key]
        return self.parent[key]

    def __setitem__(self, key, value):
        if self.parent is None or key in self.variables:
            self.variables[key] = value
        else:
            self.parent[key] = value

    def update(self, d):
        return self.variables.update(d)

    def get(self, key, default=None):
        if self.parent is None or key in self.variables:
            return self.variables[key]
        elif self.parent is not None:
            return self.parent.get(key, default)
        return default


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


def make_env():
    env = Env()
    env.permit_execution = True
    env.builtins = {
        "echo": echo,
        "local": local,
    }
    return env
