"""Picobox API to work with a box at the top of the stack."""

import threading
import functools

from ._box import Box, ChainBox


_stack = []
_lock = threading.Lock()


# An internal class that proxies all calls to its instance to a box at the top
# of the stack. The main purpose of this proxy is to be a drop-in replacement
# for a box instance to provide picobox-level set of functions that mimic Box
# interface but deal with a box at the top. While it's not completely necessary
# for methods like put() and get(), it's crucial for pass_() due to its
# lazyness.
class _topbox(object):

    def __getattribute__(self, name):
        try:
            return getattr(_stack[-1], name)

        except IndexError:
            raise RuntimeError(
                'No boxes found on stack, please use picobox.push() first.')


_topbox = _topbox()


class _push:
    """A helper context manager, that will automatically call :func:`pop`."""

    def __init__(self, box):
        self._box = box

    def __enter__(self):
        return self._box

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pop()


def push(box, chain=False):
    """Push a :class:`Box` instance to the top of the stack.

    Returns a context manager, that will automatically pop the box from the
    top of the stack on exit. Can also be used as a regular function, in
    which case it's up to callers to perform a corresponding call to
    :func:`pop()`, when they are done with the box.

    The box on the top is used by :func:`put`, :func:`get` and :func:`pass_`
    functions (not methods) and together they define a so called Picobox's
    stacked interface. The idea behind stacked interface is to provide a way
    to easily switch DI containers (boxes) without changing injections.

    Here's a minimal example of how push can be used (as a context manager)::

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

    As a regular function::

        picobox.push(foobox)
        picobox.push(barbox)

        assert do() == 14
        picobox.pop()

        assert do() == 43
        picobox.pop()

    :param box: A :class:`Box` instance to push to the top of the stack.
    :param chain: (optional) Look up missed keys one level down the stack. To
        look up through multiple levels, each level must be created with this
        option set to ``True``.
    """

    # Despite "list" is thread-safe in CPython (due to GIL), it's not
    # guaranteed by the language itself and may not be the case among
    # alternative implementations.
    with _lock:
        if chain and _stack:
            box = ChainBox(box, _stack[-1])
        _stack.append(box)

    return _push(box)


def pop():
    """Pop the box from the top of the stack.

    Should be called once for every corresponding call to :func:`push` in order
    to remove the box from the top of the stack, when a caller is done with it.

    Note, that :func:`push` should normally be used as a context manager,
    in which case the top box is removed automatically on exit from the
    with-block and there is no need to call :func:`pop` explicitly.

    :raises: IndexError: if the stack is empty and there's nothing to pop
    """
    # Despite "list" is thread-safe in CPython (due to GIL), it's not
    # guaranteed by the language itself and may not be the case among
    # alternative implementations.
    with _lock:
        return _stack.pop()


def _wraps(method):
    # The reason behind empty arguments is to reuse a signature of wrapped
    # function while preserving "__doc__", "__name__" and other accompanied
    # attributes. They are very helpful for troubleshooting as well as
    # necessary for Sphinx API reference.
    return functools.wraps(functools.partial(method, _topbox), (), ())


@_wraps(Box.put)
def put(*args, **kwargs):
    """The same as :meth:`Box.put` but for a box at the top of the stack."""
    return _topbox.put(*args, **kwargs)


@_wraps(Box.get)
def get(*args, **kwargs):
    """The same as :meth:`Box.get` but for a box at the top of the stack."""
    return _topbox.get(*args, **kwargs)


@_wraps(Box.pass_)
def pass_(*args, **kwargs):
    """The same as :meth:`Box.pass_` but for a box at the top of the stack."""
    # Box.pass_(_topbox, *args, **kwargs) does not work in Python 2 because
    # Box.pass_ is an unbound method, and unbound methods require class
    # instance as its first argument. Therefore, we need a workaround to
    # extract a function without "method" wrapping, so we can pass anything
    # as the first argument.
    return vars(Box)['pass_'](_topbox, *args, **kwargs)
