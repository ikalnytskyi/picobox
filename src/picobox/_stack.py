"""Picobox API to work with a box at the top of the stack."""

import contextlib
import functools
import threading
import typing as t

from ._box import Box, ChainBox


def _copy_signature(method, instance=None):
    # This is a workaround to overcome 'sphinx.ext.autodoc' inability to
    # retrieve a docstring of a bound method. Here's the trick - we create
    # a partial function, and autodoc can deal with partially applied
    # functions.
    if instance:
        method = functools.partial(method, instance)

    # The reason behind empty arguments is to reuse a signature of wrapped
    # function while preserving "__doc__", "__name__" and other accompanied
    # attributes. They are very helpful for troubleshooting as well as
    # necessary for Sphinx API reference.
    return functools.wraps(method, (), ())


def _create_stack_proxy(stack, empty_stack_error):
    """Create an object that proxies all calls to the top of the stack."""

    class _StackProxy:
        def __getattribute__(self, name):
            try:
                return getattr(stack[-1], name)
            except IndexError:
                raise RuntimeError(empty_stack_error)

    return _StackProxy()


@contextlib.contextmanager
def _create_push_context_manager(box, pop_callback):
    """Create a context manager that calls something on exit."""
    try:
        yield box
    finally:
        # Ensure the poped box is the same that was submitted by this exact
        # context manager. It may happen if someone messed up with order of
        # push() and pop() calls. Normally, push() should be used a context
        # manager to avoid this issue.
        assert pop_callback() is box


class Stack:
    """Stack is a dependency injection (DI) container for containers (boxes).

    While :class:`Box` is a great way to manage dependencies, it has no means
    to override them. This might be handy most of all in tests, where you
    usually need to provide a special set of dependencies configured for
    test purposes. This is where :class:`Stack` comes in. It provides the very
    same interface Box does, but proxies all calls to a box on the top.

    This basically means you can define injection points once, but change
    dependencies on the fly by changing DI containers (boxes) on the stack.
    Here's a minimal example of how a stack can be used::

        import picobox

        stack = picobox.Stack()

        @stack.pass_('magic')
        def do(magic):
            return magic + 1

        foobox = picobox.Box()
        foobox.put('magic', 42)

        barbox = picobox.Box()
        barbox.put('magic', 13)

        with stack.push(foobox):
            with stack.push(barbox):
                assert do() == 14
            assert do() == 43

    .. note::

        Usually you want to have only one stack instance to wire things up.
        That's why picobox comes with pre-created stack instance. You can
        work with that instance using :func:`push`, :func:`pop`, :func:`put`,
        :func:`get` and :func:`pass_` functions.

    :param name: (optional) A name of the stack.

    .. versionadded:: 2.2
    """

    def __init__(self, name: t.Optional[str] = None):
        self._name = name
        self._stack = []
        self._lock = threading.Lock()

        # A proxy object that proxies all calls to a box instance on the top
        # of the stack. We need such an object to provide a set of functions
        # that mimic Box interface but deal with a box on the top instead.
        # While it's not completely necessary for `put()` and `get()`, it's
        # crucial for `pass_()` due to its laziness and thus late evaluation.
        self._topbox = _create_stack_proxy(
            self._stack, "No boxes found on the stack, please `.push()` a box first."
        )

    def __repr__(self):
        name = self._name
        if not self._name:
            name = "0x%x" % id(self)
        return "<Stack (%s)>" % name

    def push(self, box: Box, *, chain: bool = False) -> t.ContextManager[Box]:
        """Push a :class:`Box` instance to the top of the stack.

        Returns a context manager, that will automatically pop the box from the
        top of the stack on exit. Can also be used as a regular function, in
        which case it's up to callers to perform a corresponding call to
        :meth:`.pop`, when they are done with the box.

        :param box: A :class:`Box` instance to push to the top of the stack.
        :param chain: (optional) Look up missed keys one level down the stack.
            To look up through multiple levels, each level must be created with
            this option set to ``True``.
        """
        # list.append() is a thread-safe operation in CPython, yet the safety
        # is not guranteed by the language itself. So the lock is used here to
        # ensure the code works properly even when running on alternative
        # implementations.
        with self._lock:
            if chain and self._stack:
                box = ChainBox(box, self._stack[-1])
            self._stack.append(box)
        return _create_push_context_manager(self._stack[-1], self._stack.pop)

    def pop(self) -> Box:
        """Pop the box from the top of the stack.

        Should be called once for every corresponding call to :meth:`.push` in
        order to remove the box from the top of the stack, when a caller is
        done with it.

        .. note::

            Normally :meth:`.push` should be used a context manager, in which
            case the box on the top is removed automatically on exit from
            the block (i.e. no need to call :meth:`.pop` manually).

        :return: a removed box
        :raises IndexError: If the stack is empty and there's nothing to pop.
        """
        # list.append() is a thread-safe operation in CPython, yet the safety
        # is not guranteed by the language itself. So the lock is used here to
        # ensure the code works properly even when running on alternative
        # implementations.
        with self._lock:
            return self._stack.pop()

    @_copy_signature(Box.put)
    def put(self, *args, **kwargs):
        """The same as :meth:`Box.put` but for a box at the top."""
        return self._topbox.put(*args, **kwargs)

    @_copy_signature(Box.get)
    def get(self, *args, **kwargs):
        """The same as :meth:`Box.get` but for a box at the top."""
        return self._topbox.get(*args, **kwargs)

    @_copy_signature(Box.pass_)
    def pass_(self, *args, **kwargs):
        """The same as :meth:`Box.pass_` but for a box at the top."""
        return Box.pass_(self._topbox, *args, **kwargs)


_instance = Stack("shared")


@_copy_signature(Stack.push, _instance)
def push(*args, **kwargs):
    """The same as :meth:`Stack.push` but for a shared stack instance.

    .. versionadded:: 1.1 ``chain`` parameter
    """
    return _instance.push(*args, **kwargs)


@_copy_signature(Stack.pop, _instance)
def pop(*args, **kwargs):
    """The same as :meth:`Stack.pop` but for a shared stack instance.

    .. versionadded:: 2.0
    """
    return _instance.pop(*args, **kwargs)


@_copy_signature(Stack.put, _instance)
def put(*args, **kwargs):
    """The same as :meth:`Stack.put` but for a shared stack instance."""
    return _instance.put(*args, **kwargs)


@_copy_signature(Stack.get, _instance)
def get(*args, **kwargs):
    """The same as :meth:`Stack.get` but for a shared stack instance."""
    return _instance.get(*args, **kwargs)


@_copy_signature(Stack.pass_, _instance)
def pass_(*args, **kwargs):
    """The same as :meth:`Stack.pass_` but for a shared stack instance."""
    return _instance.pass_(*args, **kwargs)
