import contextlib
import os
import pathlib
import tempfile
from psh.glob import start, entries, dirs_only, recurse, name_matches, STAR, STARSTAR, expand
from psh.model import Word, ConstantString
from psh.local import make_env
from psh.sentinel import Sentinel


TOUCH = Sentinel("TOUCH")


@contextlib.contextmanager
def make_dirs(*ds):
    with tempfile.TemporaryDirectory() as d:
        if len(ds) > 0:
            md = True
            for dd in ds:
                if dd is TOUCH:
                    md = False
                elif md:
                    os.makedirs(os.path.join(d, dd), exist_ok=True)
                else:
                    p = os.path.join(d, dd)
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    with open(p, "w"):
                        pass
        else:
            os.makedirs(os.path.join(d, "a", "aa", "aaa1"), exist_ok=True)
            os.makedirs(os.path.join(d, "a", "aa", "aaa2"), exist_ok=True)
            os.makedirs(os.path.join(d, "a", "ab", "aba1"), exist_ok=True)
            os.makedirs(os.path.join(d, "b", "bb", "bbb1"), exist_ok=True)
            os.makedirs(os.path.join(d, "b", "bb", "bbb2"), exist_ok=True)
        yield pathlib.Path(d)


def test_generator_chain():
    items = []
    with make_dirs() as d:
        for item in dirs_only(entries(start(d))):
            items.append(item)

    assert [item.name for item in items] == ["a", "b"]


def test_recursion():
    items = []

    with make_dirs() as d:
        for item in recurse(entries(d), entries):
            items.append(item)

    assert [item.name for item in items] == ["a", "aa", "aaa1", "aaa2", "ab", "aba1", "b", "bb", "bbb1", "bbb2"]


def test_splat_matching():
    items = []

    with make_dirs() as d:
        for item in name_matches(".*b")(recurse(entries(d), entries)):
            items.append(item)

    assert [item.name for item in items] == ["ab", "aba1", "b", "bb", "bbb1", "bbb2"]


@contextlib.contextmanager
def cwd(d):
    orig = os.open(".", os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.chdir(d)
        yield d
    finally:
        os.fchdir(orig)
        os.close(orig)


def test_word_expand():
    word = Word([ConstantString("a/b*/c"), STAR, ConstantString("d/e")])
    env = make_env()

    with make_dirs("a/b*/cfood/e", "a/b*/cd/e/f") as d:
        with cwd(d):
            ans = expand(env, word, ".")

    assert ans == ["a/b*/cd/e", "a/b*/cfood/e"]


def test_word_expand_rec():
    word = Word([ConstantString("a/"), STARSTAR, ConstantString("/e")])
    env = make_env()

    with make_dirs("a/b*/cfood/e", "a/b*/cd/e/f") as d:
        with cwd(d):
            ans = expand(env, word, ".")

    assert ans == ["a/b*/cd/e", "a/b*/cfood/e"]


def test_no_dots():
    word = Word([STAR, ConstantString("/..")])
    env = make_env()

    with make_dirs("a", "b", ".c", ".d", TOUCH, "e", ".f") as d:
        with cwd(d):
            ans = expand(env, word, ".")

    assert ans == ["a/..", "b/.."]


def test_dots():
    word = Word([ConstantString("."), STAR, ConstantString("/..")])
    env = make_env()

    with make_dirs("a", "b", ".c", ".d", TOUCH, "e", ".f") as d:
        with cwd(d):
            ans = expand(env, word, ".")

    assert ans == [".c/..", ".d/.."]


def test_files_too():
    word = Word([STAR])
    env = make_env()

    with make_dirs("a", "b", ".c", ".d", TOUCH, "e", ".f") as d:
        with cwd(d):
            ans = expand(env, word, ".")

    assert ans == ["a", "b", "e"]


def test_more_dots():
    word = Word([ConstantString("."), STAR])
    env = make_env()

    with make_dirs("a", "b", ".c", ".d", TOUCH, "e", ".f") as d:
        with cwd(d):
            ans = expand(env, word, ".")

    assert ans == [".c", ".d", ".f"]
