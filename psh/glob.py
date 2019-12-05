import functools
import inspect
import pathlib
import re

from .base import Comparable, Evaluable
from .sentinel import Sentinel


class _Star(Comparable, Evaluable, Sentinel):
    def evaluate(self, env, input=None, output=None, error=None):
        return self

    def execute(self,  env, input=None, output=None, error=None):
        raise RuntimeError("attempt to execute _Star")


STAR = _Star("{*}")


class _StarStar(Comparable, Evaluable, Sentinel):
    def evaluate(self, env, input=None, output=None, error=None):
        return self

    def execute(self,  env, input=None, output=None, error=None):
        raise RuntimeError("attempt to execute _Star")


STARSTAR = _StarStar("{**}")


# Generators.
# These may be passed a source generator to draw from.
# That source should yield the objects we're filtering on:
# for file globbing, those will be file records.
# They yield the same.
# We will compile a glob pattern into a sequence of these.


def gen(f):
    @functools.wraps(f)
    def ff(gen, *args, **kwargs):
        if not inspect.isgenerator(gen):
            gen = (gen,)
        return f(gen, *args, **kwargs)
    return ff


def start(d):
    # Just a source
    if isinstance(d, pathlib.PurePath):
        yield d
    else:
        yield pathlib.Path(d)


@gen
def recurse(gen, maker):
    for item in gen:
        yield item
        yield from recurse(maker(item), maker)


@gen
def dirs_only(gen):
    for item in gen:
        if item.is_dir():
            yield item


@gen
def entries(gen):
    for item in gen:
        if item.is_dir():
            for sub_item in sorted(item.iterdir()):
                yield sub_item


def name_matches(pattern):
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    @gen
    def name_matches(gen):
        for item in gen:
            if pattern.match(item.name):
                yield item
    return name_matches


def flatten(ls):
    return sum(ls, [])


SLASH = Sentinel("SLASH")


def explode(part):
    """If part is a bare string, split it on '/'

    If part is anything other than a string, return it."""
    if isinstance(part, str):
        ans = []
        while len(part) > 0:
            parts = part.partition("/")
            ans.append(parts[0])
            if parts[1] != "":
                ans.append(SLASH)
            part = parts[2]
        return ans

    return [part]


def compile_name_match(bits):
    r = "^"
    for b in bits:
        if b is STAR:
            r += ".*"
        else:
            r += re.escape(b)
    r += "$"
    return re.compile(r)


def expand(env, word, dir):
    """Given a word, turn it into a list of strings"""
    ans = [item.evaluate(env) for item in word]
    if STAR not in ans and STARSTAR not in ans:
        return [''.join(ans)]

    output = flatten(explode(item.evaluate(env)) for item in word)
    if output[:2] == ["", SLASH]:
        dir = "/"

    result = start(dir)
    bits = []
    rec = False
    for item in output:
        if isinstance(item, str):
            bits.append(item)
        elif item is STAR:
            bits.append(item)
        elif item is STARSTAR:
            bits.append(STAR)
            rec = True
        elif item is SLASH:
            result = entries(result)
            result = name_matches(compile_name_match(bits))(result)
            if rec:
                result = recurse(result, entries)
            bits = []
            rec = False
    else:
        if len(bits) > 0:
            result = entries(result)
            result = name_matches(compile_name_match(bits))(result)
            if rec:
                result = recurse(result, entries)

    return [str(item) for item in result]
