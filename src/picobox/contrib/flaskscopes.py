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
    """Share instances across the same Flask (HTTP) application."""

    @property
    def _store(self):
        return flask.current_app


class request(_flaskscope):
    """Share instances across the same Flask (HTTP) request."""

    @property
    def _store(self):
        return flask.g
