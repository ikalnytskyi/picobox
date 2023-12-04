"""Test ASGI scopes."""

import asyncio

import async_asgi_testclient
import pytest
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.testclient import TestClient

from picobox.ext import asgiscopes


class ClientFacade:
    """The facade around synchronous test client."""

    def __init__(self, app, connection_type):
        self._testclient = TestClient(app=app)
        self._connection_type = connection_type

    def run_endpoint(self, url):
        if self._connection_type == "http":
            response = self._testclient.get(url)

            # Make sure that no mistakes are made and requested URL is found in
            # the ASGI application. In the end, all we care is that the test is
            # executed.
            assert response.status_code == 200, response.content
        elif self._connection_type == "websocket":
            with self._testclient.websocket_connect(url):
                pass
        else:
            pytest.fail(f"{self._connection_type}: not implemented")


class AsyncClientFacade:
    """The facade around asynchronous test client."""

    def __init__(self, app, connection_type):
        self._testclient = async_asgi_testclient.TestClient(app)
        self._connection_type = connection_type

    async def run_endpoint(self, url):
        if self._connection_type == "http":
            response = await self._testclient.get(url)

            # Make sure that no mistakes are made and requested URL is found in
            # the ASGI application. In the end, all we care is that the test is
            # executed.
            assert response.status_code == 200, response.content
        elif self._connection_type == "websocket":
            async with self._testclient.websocket_connect(url):
                pass
        else:
            pytest.fail(f"{self._connection_type}: not implemented")


@pytest.fixture(params=["http", "websocket"])
def connection_type(request):
    """The connection type to run tests for."""

    return request.param


@pytest.fixture()
def app_factory(connection_type):
    """A factory that creates test application instances."""

    def factory(*routes, with_scope_middleware=True):
        app = Starlette()

        for url, func in routes:
            if connection_type == "http":

                async def endpoint_http(_, func=func):
                    return await func() or Response()

                app.router.add_route(url, endpoint_http)
            elif connection_type == "websocket":

                async def endpoint_ws(websocket, func=func):
                    await websocket.accept()
                    await func()
                    await websocket.close()

                app.router.add_websocket_route(url, endpoint_ws)
            else:
                pytest.fail(f"{connection_type}: not implemented")

        if with_scope_middleware:
            app.add_middleware(asgiscopes.ScopeMiddleware)
        return app

    return factory


@pytest.fixture()
def client_factory(connection_type):
    """A factory that creates synchronous test client instances."""

    def factory(app):
        return ClientFacade(app, connection_type)

    return factory


@pytest.fixture()
def asyncclient_factory(connection_type):
    """A factory that creates asynchronous test client instances."""

    def factory(app):
        return AsyncClientFacade(app, connection_type)

    return factory


@pytest.mark.parametrize(
    "scope_factory",
    [
        asgiscopes.application,
        asgiscopes.request,
    ],
)
def test_scope_set_key(app_factory, client_factory, scope_factory, supported_key):
    scope = scope_factory()

    async def endpoint():
        scope.set(supported_key, "the-value")
        assert scope.get(supported_key) == "the-value"

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        asgiscopes.application,
        asgiscopes.request,
    ],
)
def test_scope_set_value(app_factory, client_factory, scope_factory, supported_value):
    scope = scope_factory()

    async def endpoint():
        scope.set("the-value", supported_value)
        assert scope.get("the-value") is supported_value

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        asgiscopes.application,
        asgiscopes.request,
    ],
)
def test_scope_set_overwrite(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    async def endpoint():
        scope.set("the-key", value)
        assert scope.get("the-key") is value

        scope.set("the-key", "overwrite")
        assert scope.get("the-key") == "overwrite"

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        asgiscopes.application,
        asgiscopes.request,
    ],
)
def test_scope_get_keyerror(app_factory, client_factory, scope_factory, supported_key):
    scope = scope_factory()

    async def endpoint():
        with pytest.raises(KeyError) as excinfo:
            scope.get(supported_key)
        assert str(excinfo.value) == f"{supported_key!r}"

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        asgiscopes.application,
        asgiscopes.request,
    ],
)
def test_scope_state_not_shared_between_instances(app_factory, client_factory, scope_factory):
    scope_a = scope_factory()
    value_a = object()

    scope_b = scope_factory()
    value_b = object()

    async def endpoint():
        scope_a.set("the-key", value_a)
        assert scope_a.get("the-key") is value_a

        with pytest.raises(KeyError) as excinfo:
            scope_b.get("the-key")
        assert str(excinfo.value) == "'the-key'"

        scope_b.set("the-key", value_b)
        assert scope_b.get("the-key") is value_b

        assert scope_a.get("the-key") is value_a

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        asgiscopes.application,
    ],
)
def test_scope_value_shared(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    async def endpoint1():
        scope.set("the-key", value)

    async def endpoint2():
        assert scope.get("the-key") is value

    client = client_factory(
        app_factory(
            ("/1", endpoint1),
            ("/2", endpoint2),
        )
    )
    client.run_endpoint("/1")
    client.run_endpoint("/2")


@pytest.mark.parametrize(
    "scope_factory",
    [
        asgiscopes.request,
    ],
)
def test_scope_value_not_shared(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    async def endpoint1():
        scope.set("the-key", value)

    async def endpoint2():
        with pytest.raises(KeyError) as excinfo:
            assert scope.get("the-key") is value
        assert str(excinfo.value) == "'the-key'"

    client = client_factory(
        app_factory(
            ("/1", endpoint1),
            ("/2", endpoint2),
        )
    )
    client.run_endpoint("/1")
    client.run_endpoint("/2")


@pytest.mark.parametrize(
    "scope_factory",
    [
        asgiscopes.application,
        asgiscopes.request,
    ],
)
def test_scope_value_downstack_shared(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    async def endpoint():
        scope.set("the-key", value)
        await subroutine()

    async def subroutine():
        assert scope.get("the-key") is value

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        asgiscopes.application,
        asgiscopes.request,
    ],
)
def test_scope_value_downstack_task_shared(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    async def endpoint():
        scope.set("the-key", value)
        await asyncio.create_task(subroutine())

    async def subroutine():
        assert scope.get("the-key") is value

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        asgiscopes.application,
        asgiscopes.request,
    ],
)
def test_scope_value_upstack_shared(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    async def endpoint():
        await subroutine()
        assert scope.get("the-key") is value

    async def subroutine():
        scope.set("the-key", value)

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        asgiscopes.application,
        asgiscopes.request,
    ],
)
def test_scope_value_upstack_task_shared(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    async def endpoint():
        await asyncio.create_task(subroutine())
        assert scope.get("the-key") is value

    async def subroutine():
        scope.set("the-key", value)

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


def test_scope_application_is_application_bound(app_factory, client_factory):
    scope = asgiscopes.application()
    value = object()

    async def endpoint1():
        scope.set("the-key", value)
        assert scope.get("the-key") is value

    async def endpoint2():
        with pytest.raises(KeyError) as excinfo:
            scope.get("the-key")
        assert str(excinfo.value) == "'the-key'"

    client1 = client_factory(app_factory(("/1", endpoint1)))
    client2 = client_factory(app_factory(("/2", endpoint2)))

    client1.run_endpoint("/1")
    client2.run_endpoint("/2")


@pytest.mark.asyncio()
async def test_scope_request_is_request_bound(app_factory, asyncclient_factory):
    scope = asgiscopes.request()
    value = object()
    event1 = asyncio.Event()
    event2 = asyncio.Event()

    async def endpoint1():
        scope.set("the-key", value)
        event1.set()
        await event2.wait()
        assert scope.get("the-key") is value

    async def endpoint2():
        await event1.wait()
        with pytest.raises(KeyError, match="the-key"):
            scope.get("the-key")
        event2.set()

    client = asyncclient_factory(
        app_factory(
            ("/1", endpoint1),
            ("/2", endpoint2),
        )
    )

    await asyncio.gather(
        client.run_endpoint("/1"),
        client.run_endpoint("/2"),
    )


@pytest.mark.parametrize(
    "scope_factory",
    [
        asgiscopes.application,
        asgiscopes.request,
    ],
)
def test_scope_wo_middleware(app_factory, client_factory, scope_factory):
    scope = scope_factory()

    async def endpoint():
        with pytest.raises(RuntimeError) as excinfo:
            scope.set("the-key", "the-value")

        assert str(excinfo.value) == (
            "Working outside of ASGI context.\n"
            "\n"
            "This typically means that you attempted to use picobox with ASGI "
            "scopes, but 'picobox.ext.asgiscopes.ScopeMiddleware' has not "
            "been used with your ASGI application."
        )

    client = client_factory(app_factory(("/", endpoint), with_scope_middleware=False))
    client.run_endpoint("/")
