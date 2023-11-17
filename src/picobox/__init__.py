"""Dependency injection framework designed with Python in mind."""

from ._box import Box, ChainBox
from ._scopes import Scope, contextvars, noscope, singleton, threadlocal
from ._stack import Stack, get, pass_, pop, push, put

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
