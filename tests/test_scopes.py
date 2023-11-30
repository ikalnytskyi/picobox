"""Test picobox's scopes implementations."""

import asyncio
import contextvars
import threading

import pytest

import picobox


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


def run_in_event_loop(function, *args, **kwargs):
    if not asyncio.iscoroutinefunction(function):

        async def coroutine_function(*args, **kwargs):
            return function(*args, **kwargs)
    else:
        coroutine_function = function

    loop = asyncio.new_event_loop()
    try:
        rv = loop.run_until_complete(coroutine_function(*args, **kwargs))
    finally:
        loop.close()
    return rv


def run_in_context(function, *args, **kwargs):
    context = contextvars.copy_context()
    return context.run(function, *args, **kwargs)


@pytest.mark.parametrize(
    "scope_factory",
    [
        picobox.singleton,
        picobox.threadlocal,
        picobox.contextvars,
    ],
)
def test_scope_set_key(scope_factory, supported_key):
    scope = scope_factory()

    scope.set(supported_key, "the-value")
    assert scope.get(supported_key) == "the-value"


@pytest.mark.parametrize(
    "scope_factory",
    [
        picobox.singleton,
        picobox.threadlocal,
        picobox.contextvars,
    ],
)
def test_scope_set_value(scope_factory, supported_value):
    scope = scope_factory()

    scope.set("the-key", supported_value)
    assert scope.get("the-key") is supported_value


def test_scope_set_key_noscope(supported_key):
    scope = picobox.noscope()
    scope.set(supported_key, "the-value")

    with pytest.raises(KeyError) as excinfo:
        scope.get(supported_key)

    assert str(excinfo.value) == f"{supported_key!r}"


def test_scope_set_value_noscope(supported_value):
    scope = picobox.noscope()
    scope.set("the-key", supported_value)

    with pytest.raises(KeyError) as excinfo:
        scope.get("the-key")

    assert str(excinfo.value) == "'the-key'"


@pytest.mark.parametrize(
    "scope_factory",
    [
        picobox.singleton,
        picobox.threadlocal,
        picobox.contextvars,
    ],
)
def test_scope_set_overwrite(scope_factory):
    scope = scope_factory()
    value = object()

    scope.set("the-key", value)
    assert scope.get("the-key") is value

    scope.set("the-key", "overwrite")
    assert scope.get("the-key") == "overwrite"


@pytest.mark.parametrize(
    "scope_factory",
    [
        picobox.singleton,
        picobox.threadlocal,
        picobox.contextvars,
        picobox.noscope,
    ],
)
def test_scope_get_keyerror(scope_factory, supported_key):
    scope = scope_factory()

    with pytest.raises(KeyError) as excinfo:
        scope.get(supported_key)

    assert str(excinfo.value) == f"{supported_key!r}"


@pytest.mark.parametrize(
    "scope_factory",
    [
        picobox.singleton,
        picobox.threadlocal,
        picobox.contextvars,
    ],
)
def test_scope_state_not_shared_between_instances(scope_factory):
    scope_a = scope_factory()
    value_a = object()

    scope_b = type(scope_a)()
    value_b = object()

    scope_a.set("the-key", value_a)
    assert scope_a.get("the-key") is value_a

    with pytest.raises(KeyError) as excinfo:
        scope_b.get("the-key")
    assert str(excinfo.value) == "'the-key'"

    scope_b.set("the-key", value_b)
    assert scope_b.get("the-key") is value_b

    assert scope_a.get("the-key") is value_a


@pytest.mark.parametrize(
    ("scope_factory", "run"),
    [
        (picobox.singleton, run_in_thread),
        (picobox.singleton, run_in_event_loop),
        (picobox.singleton, run_in_context),
        (picobox.threadlocal, run_in_event_loop),
        (picobox.threadlocal, run_in_context),
    ],
)
def test_scope_value_shared(scope_factory, run):
    scope = scope_factory()
    value = object()

    run(scope.set, "the-key", value)
    assert run(scope.get, "the-key") is value


@pytest.mark.parametrize(
    ("scope_factory", "run"),
    [
        (picobox.threadlocal, run_in_thread),
        (picobox.contextvars, run_in_thread),
        (picobox.contextvars, run_in_event_loop),
        (picobox.contextvars, run_in_context),
        (picobox.noscope, run_in_thread),
        (picobox.noscope, run_in_event_loop),
        (picobox.noscope, run_in_context),
    ],
)
def test_scope_value_not_shared(scope_factory, run):
    scope = scope_factory()
    value = object()

    run(scope.set, "the-key", value)

    with pytest.raises(KeyError) as excinfo:
        run(scope.get, "the-key")

    assert str(excinfo.value) == "'the-key'"


@pytest.mark.parametrize(
    ("scope_factory", "run"),
    [
        (picobox.singleton, run_in_thread),
        (picobox.singleton, run_in_event_loop),
        (picobox.singleton, run_in_context),
        (picobox.threadlocal, run_in_thread),
        (picobox.threadlocal, run_in_event_loop),
        (picobox.threadlocal, run_in_context),
        (picobox.contextvars, run_in_thread),
        (picobox.contextvars, run_in_event_loop),
        (picobox.contextvars, run_in_context),
    ],
)
def test_scope_value_downstack_shared(scope_factory, run):
    scope = scope_factory()
    value = object()

    def caller():
        scope.set("the-key", value)
        return callee()

    def callee():
        return scope.get("the-key")

    assert run(caller) is value


@pytest.mark.parametrize(
    ("scope_factory", "run"),
    [
        (picobox.noscope, run_in_thread),
        (picobox.noscope, run_in_event_loop),
        (picobox.noscope, run_in_context),
    ],
)
def test_scope_value_downstack_not_shared(scope_factory, run):
    scope = scope_factory()
    value = object()

    def caller():
        scope.set("the-key", value)
        return callee()

    def callee():
        return scope.get("the-key")

    with pytest.raises(KeyError) as excinfo:
        run(caller)

    assert str(excinfo.value) == "'the-key'"


@pytest.mark.parametrize(
    ("scope_factory", "run"),
    [
        (picobox.singleton, run_in_thread),
        (picobox.singleton, run_in_event_loop),
        (picobox.singleton, run_in_context),
        (picobox.threadlocal, run_in_thread),
        (picobox.threadlocal, run_in_event_loop),
        (picobox.threadlocal, run_in_context),
        (picobox.contextvars, run_in_thread),
        (picobox.contextvars, run_in_event_loop),
        (picobox.contextvars, run_in_context),
    ],
)
def test_scope_value_upstack_shared(scope_factory, run):
    scope = scope_factory()
    value = object()

    def caller():
        callee()
        return scope.get("the-key")

    def callee():
        scope.set("the-key", value)

    assert run(caller) is value


@pytest.mark.parametrize(
    ("scope_factory", "run"),
    [
        (picobox.noscope, run_in_thread),
        (picobox.noscope, run_in_event_loop),
        (picobox.noscope, run_in_context),
    ],
)
def test_scope_value_upstack_not_shared(scope_factory, run):
    scope = scope_factory()
    value = object()

    def caller():
        callee()
        return scope.get("the-key")

    def callee():
        scope.set("the-key", value)

    with pytest.raises(KeyError) as excinfo:
        run(caller)

    assert str(excinfo.value) == "'the-key'"


@pytest.mark.parametrize(
    ("scope_factory", "run"),
    [
        (picobox.threadlocal, run_in_thread),
        (picobox.contextvars, run_in_thread),
        (picobox.contextvars, run_in_event_loop),
        (picobox.contextvars, run_in_context),
    ],
)
def test_scope_is_scope_bound(scope_factory, run):
    scope = scope_factory()

    run(scope.set, "the-key", "the-value")

    with pytest.raises(KeyError) as excinfo:
        run(scope.get, "the-key")

    assert str(excinfo.value) == "'the-key'"
