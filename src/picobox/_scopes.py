"""Scope interface and builtin implementations."""

import abc
import contextvars as _contextvars
import threading
import typing as t


class Scope(metaclass=abc.ABCMeta):
    """Scope is an execution context based storage interface.

    Execution context is a mechanism of storing and accessing data bound to a
    logical thread of execution. Thus, one may consider processes, threads,
    greenlets, coroutines, Flask requests to be examples of a logical thread.

    The interface provides just two methods:

     * :meth:`.set` - set execution context item
     * :meth:`.get` - get execution context item

    See corresponding methods for details below.
    """

    @abc.abstractmethod
    def set(self, key: t.Hashable, value: t.Any) -> None:
        """Bind `value` to `key` in current execution context."""

    @abc.abstractmethod
    def get(self, key: t.Hashable) -> t.Any:
        """Get `value` by `key` for current execution context."""


class singleton(Scope):
    """Share instances across application."""

    def __init__(self):
        self._store = {}

    def set(self, key: t.Hashable, value: t.Any) -> None:
        self._store[key] = value

    def get(self, key: t.Hashable) -> t.Any:
        return self._store[key]


class threadlocal(Scope):
    """Share instances across the same thread."""

    def __init__(self):
        self._local = threading.local()

    def set(self, key: t.Hashable, value: t.Any) -> None:
        try:
            store = self._local.store
        except AttributeError:
            store = self._local.store = {}
        store[key] = value

    def get(self, key: t.Hashable) -> t.Any:
        try:
            rv = self._local.store[key]
        except AttributeError:
            raise KeyError(key)
        return rv


class contextvars(Scope):
    """Share instances across the same execution context (:pep:`567`).

    Since `asyncio does support context variables`__, the scope could be used
    in asynchronous applications to share dependencies between coroutines of
    the same :class:`asyncio.Task`.

    .. __: https://docs.python.org/3/library/contextvars.html#asyncio-support

    .. versionadded:: 2.1
    """

    def __init__(self):
        self._store = {}

    def set(self, key: t.Hashable, value: t.Any) -> None:
        try:
            var = self._store[key]
        except KeyError:
            var = self._store[key] = _contextvars.ContextVar("picobox")
        var.set(value)

    def get(self, key: t.Hashable) -> t.Any:
        try:
            return self._store[key].get()
        except LookupError:
            raise KeyError(key)


class noscope(Scope):
    """Do not share instances, create them each time on demand."""

    def set(self, key: t.Hashable, value: t.Any) -> None:
        pass

    def get(self, key: t.Hashable) -> t.Any:
        raise KeyError(key)
