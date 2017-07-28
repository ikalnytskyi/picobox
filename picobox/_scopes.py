"""Scope interface and builtin implementations."""

import abc
import threading


class Scope(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def set(self, key, value):
        pass

    @abc.abstractmethod
    def get(self, key):
        pass


class singleton(Scope):

    def __init__(self):
        self._store = {}

    def set(self, key, value):
        self._store[key] = value

    def get(self, key):
        return self._store[key]


class threadlocal(Scope):

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

    def set(self, key, value):
        pass

    def get(self, key):
        raise KeyError("'%s'" % key)
