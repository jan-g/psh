import io


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
