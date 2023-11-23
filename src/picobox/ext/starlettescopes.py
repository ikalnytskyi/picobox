"""Scopes for FastAPI framework."""

import uuid
import contextvars

import picobox


_current_app_ctx = contextvars.ContextVar("current_app")


class ScopeMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        _current_app_ctx.set(self.app)
        await self.app(scope, receive, send)


class application(picobox.Scope):
    """Share instances across the same FastAPI application.

    In most cases can be used interchangeably with :class:`picobox.singleton`
    scope. Comes around when you have `multiple Flask applications`__ and you
    want to have independent instances for each Flask application, despite
    the fact they are running in the same WSGI context.

    .. __: http://flask.pocoo.org/docs/1.0/patterns/appdispatch/

    .. versionadded:: 4.1
    """

    def __init__(self):
        # Both application and request scopes are merely proxies to
        # corresponding storage objects in Flask. This means multiple
        # scope instances will share the same storage object under the
        # hood, and this is not what we want. So we need to generate
        # some unique key per scope instance and use that key to
        # distinguish dependencies stored by different scope instances.
        self._uuid = str(uuid.uuid4())

    @property
    def _current_app(self):
        try:
            current_app = _current_app_ctx.get()
        except LookupError:
            raise RuntimeError("picobox.ext.starlettescopes.ScopeMiddleware: missing middleware")
        return current_app

    def set(self, key, value):
        try:
            dependencies = self._current_app.__dependencies__
        except AttributeError:
            dependencies = self._current_app.__dependencies__ = {}

        try:
            dependencies = dependencies[self._uuid]
        except KeyError:
            dependencies = dependencies.setdefault(self._uuid, {})

        dependencies[key] = value

    def get(self, key):
        try:
            rv = self._current_app.__dependencies__[self._uuid][key]
        except (AttributeError, KeyError):
            raise KeyError(key)
        return rv


#: Share instances across the same FastAPI (HTTP) request.
#:
#: .. versionadded:: 4.1
request = picobox.contextvars
