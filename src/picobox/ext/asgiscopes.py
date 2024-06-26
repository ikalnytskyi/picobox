"""Scopes for ASGI applications."""

import contextvars
import typing as t
import weakref

import picobox

if t.TYPE_CHECKING:
    Store = weakref.WeakKeyDictionary[picobox.Scope, t.Dict[t.Hashable, t.Any]]
    StoreCtxVar = contextvars.ContextVar[Store]
    ASGIScope = t.MutableMapping[str, t.Any]
    ASGIMessage = t.MutableMapping[str, t.Any]
    ASGIReceive = t.Callable[[], t.Awaitable[ASGIMessage]]
    ASGISend = t.Callable[[ASGIMessage], t.Awaitable[None]]
    ASGIApplication = t.Callable[[ASGIScope, ASGIReceive, ASGISend], t.Awaitable[None]]


_current_app_store: "StoreCtxVar" = contextvars.ContextVar(f"{__name__}.current-app-store")
_current_req_store: "StoreCtxVar" = contextvars.ContextVar(f"{__name__}.current-req-store")


class ScopeMiddleware:
    """A ASGI middleware that defines scopes for Picobox.

    For the proper functioning of :class:`application` and :class:`request`
    scopes, it is essential to integrate this middleware into your ASGI
    application. Otherwise, the aforementioned scopes will be inoperable.

    .. code:: python

        from picobox.ext import asgiscopes
        app = asgiscopes.ScopeMiddleware(app)

    :param app: The ASGI application to wrap.
    """

    def __init__(self, app: "ASGIApplication") -> None:
        self.app = app
        # Since we want stored objects to be garbage collected as soon as the
        # storing scope instance is destroyed, scope instances have to be
        # weakly referenced.
        self.store: Store = weakref.WeakKeyDictionary()

    async def __call__(self, scope: "ASGIScope", receive: "ASGIReceive", send: "ASGISend") -> None:
        """Define scopes and invoke the ASGI application."""
        # Storing the ASGI application's scope state within a ScopeMiddleware
        # instance because it's assumed that each ASGI middleware is typically
        # applied once to a given ASGI application. By keeping the application
        # scope state in the middleware, we facilitate support for multiple
        # simultaneous ASGI applications (e.g., in nested execution scenarios).
        app_store_token = _current_app_store.set(self.store)
        req_store_token = _current_req_store.set(weakref.WeakKeyDictionary())

        try:
            await self.app(scope, receive, send)
        finally:
            _current_req_store.reset(req_store_token)
            _current_app_store.reset(app_store_token)


class _asgiscope(picobox.Scope):
    """A base class for ASGI scopes."""

    _store_cvar: "StoreCtxVar"

    @property
    def _store(self) -> t.Dict[t.Hashable, t.Any]:
        try:
            store = self._store_cvar.get()
        except LookupError:
            raise RuntimeError(
                "Working outside of ASGI context.\n"
                "\n"
                "This typically means that you attempted to use picobox with "
                "ASGI scopes, but 'picobox.ext.asgiscopes.ScopeMiddleware' has "
                "not been used with your ASGI application."
            )

        try:
            scope_store = store[self]
        except KeyError:
            scope_store = store.setdefault(self, {})
        return scope_store

    def set(self, key: t.Hashable, value: t.Any) -> None:
        self._store[key] = value

    def get(self, key: t.Hashable) -> t.Any:
        return self._store[key]


class application(_asgiscope):
    """Share instances across the same ASGI application.

    In typical scenarios, a single ASGI application exists, making this scope
    interchangeable with :class:`picobox.singleton`. However, unlike the
    latter, the application scope ensures that dependencies are bound to the
    lifespan of a specific application instance. This is particularly useful in
    testing scenarios where each test involves creating a new application
    instance or in situations where applications are nested.

    Requires :class:`ScopeMiddleware`; otherwise ``RuntimeError`` is thrown.

    .. versionadded:: 4.1
    """

    _store_cvar = _current_app_store


class request(_asgiscope):
    """Share instances across the same ASGI (HTTP/WebSocket) request.

    You might want to store your SQLAlchemy session or Request-ID per request.
    In many cases this produces much more readable code than passing the whole
    request context around.

    Requires :class:`ScopeMiddleware`; otherwise ``RuntimeError`` is thrown.

    .. versionadded:: 4.1
    """

    _store_cvar = _current_req_store
