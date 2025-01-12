"""Scopes for Flask framework."""

from __future__ import annotations

import typing
import weakref

import flask

import picobox


if typing.TYPE_CHECKING:
    from collections.abc import Hashable
    from typing import Any

    class _flask_store_obj(typing.Protocol):
        __dependencies__: weakref.WeakKeyDictionary[picobox.Scope, dict[Hashable, Any]]


class _flaskscope(picobox.Scope):
    """A base class for Flask scopes."""

    def __init__(self, store_obj: object) -> None:
        self._store_obj = typing.cast("_flask_store_obj", store_obj)

    @property
    def _store(self) -> dict[Hashable, Any]:
        try:
            store = self._store_obj.__dependencies__
        except AttributeError:
            store = self._store_obj.__dependencies__ = weakref.WeakKeyDictionary()

        try:
            scope_store = store[self]
        except KeyError:
            scope_store = store.setdefault(self, {})
        return scope_store

    def set(self, key: Hashable, value: Any) -> None:
        self._store[key] = value

    def get(self, key: Hashable) -> Any:
        return self._store[key]


class application(_flaskscope):
    """Share instances across the same Flask (HTTP) application.

    In typical scenarios, a single Flask application exists, making this scope
    interchangeable with :class:`picobox.singleton`. However, unlike the
    latter, the application scope ensures that dependencies are bound to the
    lifespan of a specific application instance. This is particularly useful in
    testing scenarios where each test involves creating a new application
    instance or in situations where you have `multiple Flask applications`__.

    .. __: https://flask.palletsprojects.com/en/3.0.x/patterns/appdispatch/

    Unlike :class:`picobox.ext.wsgiscopes.application`, it requires no WSGI
    middlewares.

    .. versionadded:: 2.2
    """

    def __init__(self) -> None:
        super().__init__(flask.current_app)


class request(_flaskscope):
    """Share instances across the same Flask (HTTP) request.

    You might want to store your SQLAlchemy session or Request-ID per request.
    In many cases this produces much more readable code than passing the whole
    request context around.

    Unlike :class:`picobox.ext.wsgiscopes.request`, it requires no WSGI
    middlewares.

    .. versionadded:: 2.2
    """

    def __init__(self) -> None:
        super().__init__(flask.g)
