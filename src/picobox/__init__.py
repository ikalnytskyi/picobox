"""Dependency injection framework designed with Python in mind."""

from ._box import Box, ChainBox
from ._scopes import Scope, singleton, threadlocal, noscope
from ._stack import push, pop, put, get, pass_

try:
    from ._scopes import contextvars
except ImportError:
    pass


__all__ = [
    'Box',
    'ChainBox',

    'Scope',
    'singleton',
    'threadlocal',
    'contextvars',
    'noscope',

    'push',
    'pop',
    'put',
    'get',
    'pass_',
]
