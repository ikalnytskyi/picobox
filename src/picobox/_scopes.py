"""Scope interface and builtin implementations."""

import abc
import threading

try:
    import contextvars as _contextvars
except ImportError:
    _contextvars = None

from . import _compat


@_compat.add_metaclass(abc.ABCMeta)
class Scope(object):
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
    def set(self, key, value):
        """Bind `value` to `key` in current execution context."""

    @abc.abstractmethod
    def get(self, key):
        """Get `value` by `key` for current execution context."""


class singleton(Scope):
    """Share instances across application."""

    def __init__(self):
        self._store = {}

    def set(self, key, value):
        self._store[key] = value

    def get(self, key):
        return self._store[key]


class threadlocal(Scope):
    """Share instances across the same thread."""

    def __init__(self):
        self._local = threading.local()

    def set(self, key, value):
        try:
            store = self._local.store
        except AttributeError:
            store = self._local.store = {}
        store[key] = value

    def get(self, key):
        try:
            rv = self._local.store[key]
        except AttributeError:
            raise KeyError("'%s'" % key)
        return rv


class contextvars(Scope):
    """Share instances across the same execution context (:pep:`567`)."""

    def __init__(self):
        self._store = {}

    def set(self, key, value):
        try:
            var = self._store[key]
        except KeyError:
            var = self._store[key] = _contextvars.ContextVar('picobox')
        var.set(value)

    def get(self, key):
        try:
            return self._store[key].get()
        except LookupError:
            raise KeyError("'%s'" % key)


class noscope(Scope):
    """Do not share instances, create them each time on demand."""

    def set(self, key, value):
        pass

    def get(self, key):
        raise KeyError("'%s'" % key)


if not _contextvars:
    del contextvars
