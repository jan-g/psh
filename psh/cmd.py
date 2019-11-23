import logging
import os
import sys
import traceback
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import Condition

from .parser import ParseError, command_sequence
from .local import make_env

LOG = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.DEBUG)
    kb = KeyBindings()

    @Condition
    def f():
        try:
            command_sequence.parse(session.default_buffer.text)
            return True
        except ParseError as e:
            return False

    @kb.add('escape', 'enter')
    def _(event):
        session.default_buffer.insert_text('\n')

    @kb.add('enter', filter=f)
    def _(event):
        session.default_buffer.validate_and_handle()

    @kb.add('escape', ' ')
    def _(event):
        try:
            command_sequence.parse(session.default_buffer.text)
        except ParseError as e:
            session.default_buffer.cursor_position = e.index

    session = PromptSession(key_bindings=kb, multiline=True)
    env = make_env()

    with os.fdopen(sys.stdout.fileno(), "wb", closefd=False) as stdout:
        try:
            while True:
                cmd = session.prompt("> ")
                try:
                    cmd = command_sequence.parse(cmd)
                except ParseError as e:
                    traceback.print_exc(file=sys.stderr)
                    continue
                try:
                    LOG.debug("RESULT={}".format(cmd.execute(env,
                                                         input=sys.stdin,
                                                         output=stdout,
                                                         error=sys.stderr)), file=sys.stderr)
                except Exception as e:
                    traceback.print_exc(file=sys.stderr)
                    continue
        except (EOFError, KeyboardInterrupt) as e:
            pass


def completer(*args, **kwargs):
    LOG.debug("in completer, args=%s, kwargs = %s", args, kwargs)
    return None


if __name__ == '__main__':
    main()
