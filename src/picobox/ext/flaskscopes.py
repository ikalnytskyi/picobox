"""Scopes for Flask framework."""

import typing as t
import uuid

import flask

import picobox


class _flaskscope(picobox.Scope):
    """A base class for Flask scopes."""

    def __init__(self, store: object) -> None:
        self._store = store
        # Both application and request scopes are merely proxies to
        # corresponding storage objects in Flask. This means multiple
        # scope instances will share the same storage object under the
        # hood, and this is not what we want. So we need to generate
        # some unique key per scope instance and use that key to
        # distinguish dependencies stored by different scope instances.
        self._uuid = str(uuid.uuid4())

    def set(self, key: t.Hashable, value: t.Any) -> None:
        try:
            dependencies = self._store.__dependencies__
        except AttributeError:
            dependencies = self._store.__dependencies__ = {}

        try:
            dependencies = dependencies[self._uuid]
        except KeyError:
            dependencies = dependencies.setdefault(self._uuid, {})

        dependencies[key] = value

    def get(self, key: t.Hashable) -> t.Any:
        try:
            rv = self._store.__dependencies__[self._uuid][key]
        except (AttributeError, KeyError):
            raise KeyError(key)
        return rv


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
