"""Dependency injection framework designed with Python in mind."""

from ._box import Box, ChainBox
from ._scopes import Scope, noscope, singleton, threadlocal
from ._stack import Stack, get, pass_, pop, push, put

try:
    from ._scopes import contextvars
except ImportError:
    pass


__all__ = [
    "Box",
    "ChainBox",
    "Scope",
    "singleton",
    "threadlocal",
    "contextvars",
    "noscope",
    "Stack",
    "push",
    "pop",
    "put",
    "get",
    "pass_",
]
