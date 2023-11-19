"""Test Flask scopes."""

import flask
import pytest

from picobox.ext import flaskscopes


@pytest.fixture()
def appscope():
    return flaskscopes.application()


@pytest.fixture()
def reqscope():
    return flaskscopes.request()


@pytest.fixture()
def flaskapp():
    return flask.Flask("test")


@pytest.fixture()
def appcontext(flaskapp):
    return flaskapp.app_context


@pytest.fixture()
def reqcontext(flaskapp):
    return flaskapp.test_request_context


@pytest.mark.parametrize(
    ("scopename", "ctx"),
    [
        ("appscope", "appcontext"),
        ("reqscope", "reqcontext"),
    ],
)
def test_scope_set(request, scopename, ctx, supported_key, supported_value):
    scope = request.getfixturevalue(scopename)
    ctxfn = request.getfixturevalue(ctx)

    with ctxfn():
        scope.set(supported_key, supported_value)
        assert scope.get(supported_key) is supported_value


@pytest.mark.parametrize(
    "scopename",
    [
        "appscope",
        "reqscope",
    ],
)
def test_scope_set_nocontext(request, scopename):
    scope = request.getfixturevalue(scopename)

    with pytest.raises(RuntimeError) as excinfo:
        scope.set("the-key", "the-value")
    excinfo.match("Working outside of application context.")


@pytest.mark.parametrize(
    ("scopename", "ctx"),
    [
        ("appscope", "appcontext"),
        ("reqscope", "reqcontext"),
    ],
)
def test_scope_set_value_overwrite(request, scopename, ctx):
    scope = request.getfixturevalue(scopename)
    ctxfn = request.getfixturevalue(ctx)
    value = object()

    with ctxfn():
        scope.set("the-key", value)
        assert scope.get("the-key") is value

        scope.set("the-key", "overwrite")
        assert scope.get("the-key") == "overwrite"


@pytest.mark.parametrize(
    ("scopename", "ctx"),
    [
        ("appscope", "appcontext"),
        ("reqscope", "reqcontext"),
    ],
)
def test_scope_get_keyerror(request, scopename, ctx, supported_key):
    scope = request.getfixturevalue(scopename)
    ctxfn = request.getfixturevalue(ctx)

    with pytest.raises(KeyError, match=repr(supported_key)):
        with ctxfn():
            scope.get(supported_key)


@pytest.mark.parametrize(
    ("scopename", "ctx"),
    [
        ("appscope", "appcontext"),
        ("reqscope", "reqcontext"),
    ],
)
def test_scope_state_not_leaked(request, scopename, ctx):
    ctxfn = request.getfixturevalue(ctx)

    scope_a = request.getfixturevalue(scopename)
    value_a = object()

    scope_b = type(scope_a)()
    value_b = object()

    with ctxfn():
        scope_a.set("the-key", value_a)
        assert scope_a.get("the-key") is value_a

        with pytest.raises(KeyError, match="the-key"):
            scope_b.get("the-key")

        scope_b.set("the-key", value_b)
        assert scope_b.get("the-key") is value_b

        scope_a.set("the-key", value_a)
        assert scope_a.get("the-key") is value_a


@pytest.mark.parametrize(
    ("scopename", "ctx"),
    [
        ("appscope", "appcontext"),
    ],
)
def test_scope_value_shared(request, scopename, ctx):
    scope = request.getfixturevalue(scopename)
    ctxfn = request.getfixturevalue(ctx)
    value = object()

    with ctxfn():
        scope.set("the-key", value)

    with ctxfn():
        assert scope.get("the-key") is value


@pytest.mark.parametrize(
    ("scopename", "ctx"),
    [
        ("reqscope", "reqcontext"),
    ],
)
def test_scope_value_not_shared(request, scopename, ctx):
    scope = request.getfixturevalue(scopename)
    ctxfn = request.getfixturevalue(ctx)

    with ctxfn():
        scope.set("the-key", "the-value")

    with pytest.raises(KeyError, match="the-key"):
        with ctxfn():
            scope.get("the-key")


def test_scope_value_not_shared_between_apps(appscope):
    eggs = flask.Flask("eggs")
    rice = flask.Flask("rice")
    value = object()

    with eggs.app_context():
        appscope.set("the-key", value)

    with eggs.app_context():
        assert appscope.get("the-key") is value

    with pytest.raises(KeyError, match="the-key"):
        with rice.app_context():
            appscope.get("the-key")

    with eggs.app_context():
        assert appscope.get("the-key") is value
