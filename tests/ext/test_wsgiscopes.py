"""Test WSGI scopes."""

import concurrent.futures
import threading

import flask
import flask.testing
import pytest

from picobox.ext import wsgiscopes


class ClientFacade:
    """The facade around test client."""

    def __init__(self, app):
        self._testclient = app.test_client()

    def run_endpoint(self, url):
        response = self._testclient.get(url)

        # Make sure that no mistakes are made and requested URL is found in
        # the WSGI application. In the end, all we care is that the test is
        # executed.
        assert response.status_code == 200, response.content


def run_in_thread(function, *args, **kwargs):
    closure = {}

    def target():
        try:
            closure["ret"] = function(*args, **kwargs)
        except Exception as e:
            closure["exc"] = e

    worker = threading.Thread(target=target)
    worker.start()
    worker.join()

    if "exc" in closure:
        raise closure["exc"]
    return closure["ret"]


@pytest.fixture()
def app_factory():
    """A factory that creates test application instances."""

    def factory(*routes, with_scope_middleware=True):
        app = flask.Flask("testapp")

        for rule, func in routes:

            def view_func(func=func):
                return func() or ""

            app.add_url_rule(rule, endpoint=rule, view_func=view_func)

        if with_scope_middleware:
            app.wsgi_app = wsgiscopes.ScopeMiddleware(app.wsgi_app)

        # Since tests below use 'assert' statements inside the routes, we want
        # these assertion errors from the routes to be propagated all the way
        # up to tests and not being converted into '500 Internal Server Error'.
        app.config["PROPAGATE_EXCEPTIONS"] = True
        return app

    return factory


@pytest.fixture()
def client_factory():
    """A factory that creates test client instances."""

    def factory(app):
        return ClientFacade(app)

    return factory


@pytest.mark.parametrize(
    "scope_factory",
    [
        wsgiscopes.application,
        wsgiscopes.request,
    ],
)
def test_scope_set_key(app_factory, client_factory, scope_factory, supported_key):
    scope = scope_factory()

    def endpoint():
        scope.set(supported_key, "the-value")
        assert scope.get(supported_key) == "the-value"

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        wsgiscopes.application,
        wsgiscopes.request,
    ],
)
def test_scope_set_value(app_factory, client_factory, scope_factory, supported_value):
    scope = scope_factory()

    def endpoint():
        scope.set("the-value", supported_value)
        assert scope.get("the-value") is supported_value

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        wsgiscopes.application,
        wsgiscopes.request,
    ],
)
def test_scope_set_overwrite(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    def endpoint():
        scope.set("the-key", value)
        assert scope.get("the-key") is value

        scope.set("the-key", "overwrite")
        assert scope.get("the-key") == "overwrite"

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        wsgiscopes.application,
        wsgiscopes.request,
    ],
)
def test_scope_get_keyerror(app_factory, client_factory, scope_factory, supported_key):
    scope = scope_factory()

    def endpoint():
        with pytest.raises(KeyError) as excinfo:
            scope.get(supported_key)
        assert str(excinfo.value) == f"{supported_key!r}"

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        wsgiscopes.application,
        wsgiscopes.request,
    ],
)
def test_scope_state_not_shared_between_instances(app_factory, client_factory, scope_factory):
    scope_a = scope_factory()
    value_a = object()

    scope_b = scope_factory()
    value_b = object()

    def endpoint():
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
        wsgiscopes.application,
    ],
)
def test_scope_value_shared(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    def endpoint1():
        scope.set("the-key", value)

    def endpoint2():
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
        wsgiscopes.request,
    ],
)
def test_scope_value_not_shared(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    def endpoint1():
        scope.set("the-key", value)

    def endpoint2():
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
        wsgiscopes.application,
        wsgiscopes.request,
    ],
)
def test_scope_value_downstack_shared(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    def endpoint():
        scope.set("the-key", value)
        subroutine()

    def subroutine():
        assert scope.get("the-key") is value

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        wsgiscopes.application,
        wsgiscopes.request,
    ],
)
def test_scope_value_downstack_thread_shared(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    def endpoint():
        scope.set("the-key", value)
        run_in_thread(subroutine)

    def subroutine():
        with pytest.raises(RuntimeError) as excinfo:
            assert scope.get("the-key") is value

        assert str(excinfo.value) == (
            "Working outside of WSGI context.\n"
            "\n"
            "This typically means that you attempted to use picobox with WSGI "
            "scopes, but 'picobox.ext.wsgiscopes.ScopeMiddleware' has not "
            "been used with your WSGI application."
        )

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        wsgiscopes.application,
        wsgiscopes.request,
    ],
)
def test_scope_value_upstack_shared(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    def endpoint():
        subroutine()
        assert scope.get("the-key") is value

    def subroutine():
        scope.set("the-key", value)

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


@pytest.mark.parametrize(
    "scope_factory",
    [
        wsgiscopes.application,
        wsgiscopes.request,
    ],
)
def test_scope_value_upstack_thread_shared(app_factory, client_factory, scope_factory):
    scope = scope_factory()
    value = object()

    def endpoint():
        run_in_thread(subroutine)

    def subroutine():
        with pytest.raises(RuntimeError) as excinfo:
            scope.set("the-key", value)

        assert str(excinfo.value) == (
            "Working outside of WSGI context.\n"
            "\n"
            "This typically means that you attempted to use picobox with WSGI "
            "scopes, but 'picobox.ext.wsgiscopes.ScopeMiddleware' has not "
            "been used with your WSGI application."
        )

    client = client_factory(app_factory(("/", endpoint)))
    client.run_endpoint("/")


def test_scope_application_is_application_bound(app_factory, client_factory):
    scope = wsgiscopes.application()
    value = object()

    def endpoint1():
        scope.set("the-key", value)
        assert scope.get("the-key") is value

    def endpoint2():
        with pytest.raises(KeyError) as excinfo:
            scope.get("the-key")
        assert str(excinfo.value) == "'the-key'"

    client1 = client_factory(app_factory(("/1", endpoint1)))
    client2 = client_factory(app_factory(("/2", endpoint2)))

    client1.run_endpoint("/1")
    client2.run_endpoint("/2")


def test_scope_request_is_request_bound(app_factory, client_factory):
    scope = wsgiscopes.request()
    value = object()
    event1 = threading.Event()
    event2 = threading.Event()

    def endpoint1():
        scope.set("the-key", value)
        event1.set()
        event2.wait(timeout=1)
        assert scope.get("the-key") is value

    def endpoint2():
        event1.wait(timeout=1)
        with pytest.raises(KeyError) as excinfo:
            scope.get("the-key")
        assert str(excinfo.value) == "'the-key'"
        event2.set()

    client = client_factory(
        app_factory(
            ("/1", endpoint1),
            ("/2", endpoint2),
        )
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(client.run_endpoint, "/1")
        future2 = executor.submit(client.run_endpoint, "/2")

        for future in concurrent.futures.as_completed({future1, future2}):
            future.result()


@pytest.mark.parametrize(
    "scope_factory",
    [
        wsgiscopes.application,
        wsgiscopes.request,
    ],
)
def test_scope_wo_middleware(app_factory, client_factory, scope_factory):
    scope = scope_factory()

    def endpoint():
        with pytest.raises(RuntimeError) as excinfo:
            scope.set("the-key", "the-value")

        assert str(excinfo.value) == (
            "Working outside of WSGI context.\n"
            "\n"
            "This typically means that you attempted to use picobox with WSGI "
            "scopes, but 'picobox.ext.wsgiscopes.ScopeMiddleware' has not "
            "been used with your WSGI application."
        )

    client = client_factory(app_factory(("/", endpoint), with_scope_middleware=False))
    client.run_endpoint("/")
