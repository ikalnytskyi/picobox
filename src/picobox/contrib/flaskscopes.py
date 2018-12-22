"""Scopes for Flask framework."""

import picobox
import flask


class _flaskscope(picobox.Scope):
    """A base class for Flask scopes."""

    _store = None

    def set(self, key, value):
        try:
            dependencies = self._store.__dependencies__
        except AttributeError:
            dependencies = self._store.__dependencies__ = {}
        dependencies[key] = value

    def get(self, key):
        try:
            rv = self._store.__dependencies__[key]
        except AttributeError:
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
