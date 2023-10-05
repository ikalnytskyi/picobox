"""Scopes for Flask framework."""

import uuid

import flask

import picobox


class _flaskscope(picobox.Scope):
    """A base class for Flask scopes."""

    _store = None

    def __init__(self):
        # Both application and request scopes are merely proxies to
        # corresponding storage objects in Flask. This means multiple
        # scope instances will share the same storage object under the
        # hood, and this is not what we want. So we need to generate
        # some unique key per scope instance and use that key to
        # distinguish dependencies stored by different scope instances.
        self._uuid = str(uuid.uuid4())

    def set(self, key, value):
        try:
            dependencies = self._store.__dependencies__
        except AttributeError:
            dependencies = self._store.__dependencies__ = {}

        try:
            dependencies = dependencies[self._uuid]
        except KeyError:
            dependencies = dependencies.setdefault(self._uuid, {})

        dependencies[key] = value

    def get(self, key):
        try:
            rv = self._store.__dependencies__[self._uuid][key]
        except (AttributeError, KeyError):
            raise KeyError(key)
        return rv


class application(_flaskscope):
    """Share instances across the same Flask (HTTP) application.

    In most cases can be used interchangeably with :class:`picobox.singleton`
    scope. Comes around when you have `multiple Flask applications`__ and you
    want to have independent instances for each Flask application, despite
    the fact they are running in the same WSGI context.

    .. __: http://flask.pocoo.org/docs/1.0/patterns/appdispatch/

    .. versionadded:: 2.2
    """

    @property
    def _store(self):
        return flask.current_app


class request(_flaskscope):
    """Share instances across the same Flask (HTTP) request.

    .. versionadded:: 2.2
    """

    @property
    def _store(self):
        return flask.g
