"""Picobox API to work with a box at the top of the stack."""

from __future__ import annotations

import contextlib
import threading
import typing

from ._box import Box, ChainBox, _unset

if typing.TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Generator, Hashable
    from contextlib import AbstractContextManager
    from typing import Any, ParamSpec, TypeVar, Union

    from ._scopes import Scope

    P = ParamSpec("P")
    T = TypeVar("T")
    R = Union[T | Awaitable[T]]

_ERROR_MESSAGE_EMPTY_STACK = "No boxes found on the stack, please `.push()` a box first."


@contextlib.contextmanager
def _create_push_context_manager(
    box: Box,
    pop_callback: Callable[[], Box],
) -> Generator[Box, None, None]:
    """Create a context manager that calls something on exit."""
    try:
        yield box
    finally:
        if pop_callback() is not box:
            error_message = (
                "The .push() context manager has popped the wrong Box instance, "
                "meaning it did not pop the one that was pushed. This could "
                "occur if the .push() context manager is manipulated manually "
                "instead of using the 'with' statement."
            )
            raise RuntimeError(error_message) from None


class _CurrentBoxProxy(Box):
    """Delegates operations to the Box instance at the top of the stack."""

    def __init__(self, stack: list[Box]) -> None:
        self._stack = stack

    def __getattribute__(self, name: str) -> Any:
        if name == "_stack":
            return super().__getattribute__(name)

        try:
            return getattr(self._stack[-1], name)
        except IndexError:
            raise RuntimeError(_ERROR_MESSAGE_EMPTY_STACK) from None


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

    def __init__(self, name: str | None = None) -> None:
        self._name = name or f"0x{id(self):x}"
        self._stack: list[Box] = []
        self._lock = threading.Lock()

        # A proxy object that proxies all calls to a box instance on the top
        # of the stack. We need such an object to provide a set of functions
        # that mimic Box interface but deal with a box on the top instead.
        # While it's not completely necessary for `put()` and `get()`, it's
        # crucial for `pass_()` due to its laziness and thus late evaluation.
        self._current_box = _CurrentBoxProxy(self._stack)

    def __repr__(self) -> str:
        return f"<Stack ({self._name})>"

    def push(self, box: Box, *, chain: bool = False) -> AbstractContextManager[Box]:
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
            try:
                return self._stack.pop()
            except IndexError:
                raise RuntimeError(_ERROR_MESSAGE_EMPTY_STACK) from None

    def put(
        self,
        key: Hashable,
        value: Any = _unset,
        *,
        factory: Callable[[], Any] | None = None,
        scope: type[Scope] | None = None,
    ) -> None:
        """The same as :meth:`Box.put` but for a box at the top of the stack."""
        return self._current_box.put(key, value, factory=factory, scope=scope)

    def get(self, key: Hashable, default: Any = _unset) -> Any:
        """The same as :meth:`Box.get` but for a box at the top."""
        return self._current_box.get(key, default=default)

    def pass_(
        self,
        key: Hashable,
        *,
        as_: str | None = None,
    ) -> Callable[[Callable[P, R[T]]], Callable[P, R[T]]]:
        """The same as :meth:`Box.pass_` but for a box at the top."""
        return Box.pass_(self._current_box, key, as_=as_)


_instance = Stack("shared")


def push(box: Box, *, chain: bool = False) -> AbstractContextManager[Box]:
    """The same as :meth:`Stack.push` but for a shared stack instance.

    .. versionadded:: 1.1 ``chain`` parameter
    """
    return _instance.push(box, chain=chain)


def pop() -> Box:
    """The same as :meth:`Stack.pop` but for a shared stack instance.

    .. versionadded:: 2.0
    """
    return _instance.pop()


def put(
    key: Hashable,
    value: Any = _unset,
    *,
    factory: Callable[[], Any] | None = None,
    scope: type[Scope] | None = None,
) -> None:
    """The same as :meth:`Stack.put` but for a shared stack instance."""
    return _instance.put(key, value, factory=factory, scope=scope)


def get(key: Hashable, default: Any = _unset) -> Any:
    """The same as :meth:`Stack.get` but for a shared stack instance."""
    return _instance.get(key, default=default)


def pass_(
    key: Hashable,
    *,
    as_: str | None = None,
) -> Callable[[Callable[P, R[T]]], Callable[P, R[T]]]:
    """The same as :meth:`Stack.pass_` but for a shared stack instance."""
    return _instance.pass_(key, as_=as_)
