"""Test picobox's scopes implementations."""

import asyncio
import threading

import pytest
import picobox


@pytest.fixture(scope='function')
def singleton():
    return picobox.singleton()


@pytest.fixture(scope='function')
def threadlocal():
    return picobox.threadlocal()


@pytest.fixture(scope='function')
def noscope():
    return picobox.noscope()


@pytest.fixture(scope='function')
def exec_thread():
    """Run a given callback in a separate OS thread."""
    def executor(callback, *args, **kwargs):
        ret = None
        exc = None

        def target():
            nonlocal ret, exc
            try:
                ret = callback(*args, **kwargs)
            except Exception as e:
                exc = e

        worker = threading.Thread(target=target)
        worker.start()
        worker.join()

        if exc:
            raise exc
        return ret
    return executor


@pytest.fixture(scope='function')
def exec_coroutine(request):
    """Run a given coroutine function in a separate event loop."""
    loop = asyncio.new_event_loop()
    request.addfinalizer(loop.close)

    def executor(coroutine_function, *args, **kwargs):
        if not asyncio.iscoroutinefunction(coroutine_function):
            coroutine_function = asyncio.coroutine(coroutine_function)
        return loop.run_until_complete(coroutine_function(*args, **kwargs))
    return executor


@pytest.mark.parametrize('scopename', [
    'singleton',
    'threadlocal',
])
def test_scope_set_key(request, scopename, supported_key):
    scope = request.getfixturevalue(scopename)
    value = object()

    scope.set(supported_key, value)
    assert scope.get(supported_key) is value


@pytest.mark.parametrize('scopename', [
    'singleton',
    'threadlocal',
])
def test_scope_set_value(request, scopename, supported_value):
    scope = request.getfixturevalue(scopename)

    scope.set('the-key', supported_value)
    assert scope.get('the-key') is supported_value


def test_scope_set_value_noscope():
    scope = picobox.noscope()
    scope.set('the-key', 'the-value')

    with pytest.raises(KeyError, match='the-key'):
        scope.get('the-key')


@pytest.mark.parametrize('scopename', [
    'singleton',
    'threadlocal',
])
def test_scope_set_value_overwrite(request, scopename):
    scope = request.getfixturevalue(scopename)
    value = object()

    scope.set('the-key', value)
    assert scope.get('the-key') is value

    scope.set('the-key', 'overwrite')
    assert scope.get('the-key') == 'overwrite'


@pytest.mark.parametrize('scopename', [
    'singleton',
    'threadlocal',
    'noscope',
])
def test_scope_get_keyerror(request, scopename):
    scope = request.getfixturevalue(scopename)

    with pytest.raises(KeyError, match='the-key'):
        scope.get('the-key')


@pytest.mark.parametrize('scopename', [
    'singleton',
    'threadlocal',
])
def test_scope_state_not_leaked(request, scopename):
    scope_a = request.getfixturevalue(scopename)
    value_a = object()

    scope_b = type(scope_a)()
    value_b = object()

    scope_a.set('the-key', value_a)
    assert scope_a.get('the-key') is value_a

    with pytest.raises(KeyError, match='the-key'):
        scope_b.get('the-key')

    scope_b.set('the-key', value_b)
    assert scope_b.get('the-key') is value_b

    scope_a.set('the-key', value_a)
    assert scope_a.get('the-key') is value_a


@pytest.mark.parametrize('scopename, executor', [
    ('singleton',    'exec_thread'),
    ('singleton',    'exec_coroutine'),
    ('threadlocal',  'exec_coroutine'),
])
def test_scope_value_shared(request, scopename, executor):
    scope = request.getfixturevalue(scopename)
    value = object()
    exec_ = request.getfixturevalue(executor)

    exec_(scope.set, 'the-key', value)
    assert exec_(scope.get, 'the-key') is value


@pytest.mark.parametrize('scopename, executor', [
    ('threadlocal',  'exec_thread'),
    ('noscope',      'exec_thread'),
    ('noscope',      'exec_coroutine'),
])
def test_scope_value_not_shared(request, scopename, executor):
    scope = request.getfixturevalue(scopename)
    value = object()
    exec_ = request.getfixturevalue(executor)

    exec_(scope.set, 'the-key', value)

    with pytest.raises(KeyError, match='the-key'):
        exec_(scope.get, 'the-key')


@pytest.mark.parametrize('scopename, executor', [
    ('singleton',    'exec_thread'),
    ('singleton',    'exec_coroutine'),
    ('threadlocal',  'exec_thread'),
    ('threadlocal',  'exec_coroutine'),
])
def test_scope_value_downstack_shared(request, scopename, executor):
    scope = request.getfixturevalue(scopename)
    value = object()
    exec_ = request.getfixturevalue(executor)

    def caller():
        scope.set('the-key', value)
        return callee()

    def callee():
        return scope.get('the-key')

    assert exec_(caller) is value


@pytest.mark.parametrize('scopename, executor', [
    ('noscope',      'exec_thread'),
    ('noscope',      'exec_coroutine'),
])
def test_scope_value_downstack_not_shared(request, scopename, executor):
    scope = request.getfixturevalue(scopename)
    value = object()
    exec_ = request.getfixturevalue(executor)

    def caller():
        scope.set('the-key', value)
        return callee()

    def callee():
        return scope.get('the-key')

    with pytest.raises(KeyError, match='the-key'):
        exec_(caller)


@pytest.mark.parametrize('scopename, executor', [
    ('threadlocal',  'exec_thread'),
])
def test_scope_not_leaked(request, scopename, executor):
    scope = request.getfixturevalue(scopename)
    exec_ = request.getfixturevalue(executor)

    scope.set('a-key', 'a-value')
    exec_(scope.set, 'the-key', 'the-value')

    with pytest.raises(KeyError, match='the-key'):
        scope.get('the-key')
