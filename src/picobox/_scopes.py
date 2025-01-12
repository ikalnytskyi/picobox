"""Scope interface and builtin implementations."""

from __future__ import annotations

import abc
import contextvars as _contextvars
import threading
import typing
import weakref


if typing.TYPE_CHECKING:
    from collections.abc import Hashable
    from typing import Any


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
    def set(self, key: Hashable, value: Any) -> None:
        """Bind `value` to `key` in current execution context."""

    @abc.abstractmethod
    def get(self, key: Hashable) -> Any:
        """Get `value` by `key` for current execution context."""


class singleton(Scope):
    """Share instances across application."""

    def __init__(self) -> None:
        self._store: dict[Hashable, Any] = {}

    def set(self, key: Hashable, value: Any) -> None:
        self._store[key] = value

    def get(self, key: Hashable) -> Any:
        return self._store[key]


class threadlocal(Scope):
    """Share instances across the same thread."""

    def __init__(self) -> None:
        self._local = threading.local()

    def set(self, key: Hashable, value: Any) -> None:
        try:
            store = self._local.store
        except AttributeError:
            store = self._local.store = {}
        store[key] = value

    def get(self, key: Hashable) -> Any:
        try:
            rv = self._local.store[key]
        except AttributeError:
            raise KeyError(key) from None
        return rv


class contextvars(Scope):
    """Share instances across the same execution context (:pep:`567`).

    Since `asyncio does support context variables`__, the scope could be used
    in asynchronous applications to share dependencies between coroutines of
    the same :class:`asyncio.Task`.

    .. __: https://docs.python.org/3/library/contextvars.html#asyncio-support

    .. versionadded:: 2.1
    """

    _store_obj: weakref.WeakKeyDictionary[Scope, dict[Hashable, _contextvars.ContextVar[Any]]]
    _store_obj = weakref.WeakKeyDictionary()

    @property
    def _store(self) -> dict[Hashable, _contextvars.ContextVar[Any]]:
        try:
            scope_store = self._store_obj[self]
        except KeyError:
            scope_store = self._store_obj[self] = {}
        return scope_store

    def set(self, key: Hashable, value: Any) -> None:
        self._store[key] = _contextvars.ContextVar(str(key))
        self._store[key].set(value)

    def get(self, key: Hashable) -> Any:
        try:
            return self._store[key].get()
        except LookupError:
            raise KeyError(key) from None


class noscope(Scope):
    """Do not share instances, create them each time on demand."""

    def set(self, key: Hashable, value: Any) -> None:
        pass

    def get(self, key: Hashable) -> Any:
        raise KeyError(key)
