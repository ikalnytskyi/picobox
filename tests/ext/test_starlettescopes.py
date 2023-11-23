"""Test Starlette scopes."""

import typing as t

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import Response
from starlette.endpoints import HTTPEndpoint
from starlette.testclient import TestClient

from picobox.ext import starlettescopes


# TODO:

# scope tests
#   * supported_key, supported_value
#   * application scope preserves between requests
#   * application scope is per application
#   * application scope instances is not leaking
#
#   * request scope is not preserved between requests
#   * request scope is per request (value is restored in async framework)
#   * request scope instances is not leaking


@pytest.fixture(params=["sync", "async"])
def app_factory(request: pytest.FixtureRequest) -> t.Callable[..., Starlette]:
    """Create and return test starlette application."""

    def factory(test, subtest=None):
        class TestEndpoint(HTTPEndpoint):
            if request.param == "sync":

                def get(self, request: Request) -> Response:
                    return Response(test())
            else:

                async def get(self, request: Request) -> Response:
                    return Response(test())

        class SubTestEndpoint(HTTPEndpoint):
            if request.param == "sync":

                def get(self, request: Request) -> Response:
                    return Response(subtest and subtest())
            else:

                async def get(self, request: Request) -> Response:
                    return Response(subtest and subtest())

        return Starlette(
            routes=[
                Route("/test", TestEndpoint),
                Route("/subtest", SubTestEndpoint),
            ],
            middleware=[Middleware(starlettescopes.ScopeMiddleware)],
        )

    return factory


@pytest.mark.parametrize(
    "scope_factory",
    [
        starlettescopes.application,
        starlettescopes.request,
    ],
)
def test_scope_set(app_factory, scope_factory, supported_key, supported_value):
    scope = scope_factory()

    def test():
        scope.set(supported_key, supported_value)
        assert scope.get(supported_key) is supported_value

    client = TestClient(app_factory(test))
    client.get("/test")


@pytest.mark.parametrize(
    "scope_factory",
    [
        starlettescopes.application,
        starlettescopes.request,
    ],
)
def test_scope_set_overwrite(app_factory, scope_factory):
    scope = scope_factory()
    value = object()

    def test():
        scope.set("the-key", value)
        assert scope.get("the-key") is value

        scope.set("the-key", "overwrite")
        assert scope.get("the-key") == "overwrite"

    client = TestClient(app_factory(test))
    client.get("/test")


@pytest.mark.parametrize(
    "scope_factory",
    [
        starlettescopes.application,
        starlettescopes.request,
    ],
)
def test_scope_get_keyerror(app_factory, scope_factory, supported_key):
    scope = scope_factory()

    def test():
        with pytest.raises(KeyError, match=repr(supported_key)):
            scope.get(supported_key)

    client = TestClient(app_factory(test))
    client.get("/test")


@pytest.mark.parametrize(
    "scope_factory",
    [
        starlettescopes.application,
        starlettescopes.request,
    ],
)
def test_scope_state_not_leaked(app_factory, scope_factory):
    scope_a = scope_factory()
    value_a = object()

    scope_b = scope_factory()
    value_b = object()

    def test():
        scope_a.set("the-key", value_a)
        assert scope_a.get("the-key") is value_a

        with pytest.raises(KeyError, match="the-key"):
            scope_b.get("the-key")

        scope_b.set("the-key", value_b)
        assert scope_b.get("the-key") is value_b

        scope_a.set("the-key", value_a)
        assert scope_a.get("the-key") is value_a

    client = TestClient(app_factory(test))
    client.get("/test")


@pytest.mark.parametrize(
    "scope_factory",
    [
        starlettescopes.application,
    ],
)
def test_scope_value_shared(app_factory, scope_factory):
    scope = scope_factory()
    value = object()

    def test():
        scope.set("the-key", value)

    def subtest():
        assert scope.get("the-key") is value

    client = TestClient(app_factory(test, subtest))
    client.get("/test")
    client.get("/subtest")


@pytest.mark.parametrize(
    "scope_factory",
    [
        starlettescopes.request,
    ],
)
def test_scope_value_not_shared(app_factory, scope_factory):
    scope = scope_factory()
    value = object()

    def test():
        scope.set("the-key", value)

    def subtest():
        with pytest.raises(KeyError, match="the-key"):
            assert scope.get("the-key") is value

    client = TestClient(app_factory(test, subtest))
    client.get("/test")
    client.get("/subtest")


@pytest.mark.parametrize(
    "scope_factory",
    [
        starlettescopes.application,
        starlettescopes.request,
    ],
)
def test_scope_value_downstack_shared(app_factory, scope_factory):
    scope = scope_factory()
    value = object()

    def test():
        scope.set("the-key", value)
        client.get("/subtest")

    def subtest():
        assert scope.get("the-key") is value

    client = TestClient(app_factory(test, subtest))
    client.get("/test")


# def test_scope_not_leaked(request, scopename, executor):
#     scope = request.getfixturevalue(scopename)
#     exec_ = request.getfixturevalue(executor)
# 
#     scope.set("a-key", "a-value")
#     exec_(scope.set, "the-key", "the-value")
# 
#     with pytest.raises(KeyError, match="the-key"):
#         scope.get("the-key")
