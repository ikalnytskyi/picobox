"""Picobox API to work with a box at the top of the stack."""

import threading
import functools

from ._box import Box


_stack = []


# An internal class that proxies all calls to its instance to a box at the top
# of the stack. The main purpose of this proxy is to be a drop-in replacement
# for a box instance to provide picobox-level set of functions that mimic Box
# interface but deal with a box at the top. While it's not completely necessary
# for methods like put() and get(), it's crucial for pass_() due to its
# lazyness.
class _topbox:

    def __getattribute__(self, name):
        try:
            return getattr(_stack[-1], name)

        except IndexError:
            raise RuntimeError(
                'No boxes found on stack, please use picobox.push() first.')


_topbox = _topbox()


class push:
    """Context manager to push a :class:`Box` instance to the top of the stack.

    The box on the top is used by :func:`put`, :func:`get` and :func:`pass_`
    functions (not methods) and together they define a so called Picobox's
    stacked interface. The idea behind stacked interface is to provide a way
    to easily switch DI containers (boxes) without changing injections.

    Here's a minimal example of how push can be used::

        import picobox

        @picobox.pass_('magic')
        def do(magic):
            return magic + 1

        foobox = picobox.Box()
        foobox.put('magic', 42)

        barbox = picobox.Box()
        barbox.put('magic', 13)

        with picobox.push(foobox):
            with picobox.push(barbox):
                assert do() == 14
            assert do() == 43
    """

    def __init__(self, box):
        self._lock = threading.Lock()
        self._box = box

    def __enter__(self):
        # Despite "list" is thread-safe in CPython (due to GIL), it's not
        # guaranteed by the language itself and may not be the case among
        # alternative implementations.
        with self._lock:
            _stack.append(self._box)
        return self._box

    def __exit__(self, exc_type, exc_value, exc_traceback):
        # Despite "list" is thread-safe in CPython (due to GIL), it's not
        # guaranteed by the language itself and may not be the case among
        # alternative implementations.
        with self._lock:
            _stack.pop()


def _wraps(method):
    # The reason behind empty arguments is to reuse a signature of wrapped
    # function while preserving "__doc__", "__name__" and other accompanied
    # attributes. They are very helpful for troubleshooting as well as
    # necessary for Sphinx API reference.
    return functools.wraps(functools.partial(method, _topbox), (), ())


@_wraps(Box.put)
def put(*args, **kwargs):
    """The same as :meth:`Box.put` but for a box at the top of the stack."""
    return Box.put(_topbox, *args, **kwargs)


@_wraps(Box.get)
def get(*args, **kwargs):
    """The same as :meth:`Box.get` but for a box at the top of the stack."""
    return Box.get(_topbox, *args, **kwargs)


@_wraps(Box.pass_)
def pass_(*args, **kwargs):
    """The same as :meth:`Box.pass_` but for a box at the top of the stack."""
    return Box.pass_(_topbox, *args, **kwargs)
