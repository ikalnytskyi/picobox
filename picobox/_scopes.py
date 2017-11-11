"""Scope interface and builtin implementations."""

import abc
import threading


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
        self._store = threading.local()

    def set(self, key, value):
        setattr(self._store, key, value)

    def get(self, key):
        try:
            rv = getattr(self._store, key)
        except AttributeError:
            raise KeyError("'%s'" % key)
        return rv


class noscope(Scope):
    """Do not share instances, create them each time on demand."""

    def set(self, key, value):
        pass

    def get(self, key):
        raise KeyError("'%s'" % key)
