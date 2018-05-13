"""Setup pytest environment."""

import pytest
import picobox


@pytest.fixture(scope='function', params=[
    42,
    '42',
    42.42,
    True,
    None,
    (1, None, True),
    object(),
])
def hashable_value(request):
    return request.param


@pytest.fixture(scope='function', params=[
    42,
    '42',
    42.42,
    True,
    None,
    {'a': 1, 'b': 2},
    {'a', 'b', 'c'},
    [1, 2, 'c'],
    (1, None, True),
    object(),
    lambda: 42,
])
def any_value(request):
    return request.param


@pytest.fixture(scope='function')
def supported_key(hashable_value):
    return hashable_value


@pytest.fixture(scope='function')
def supported_value(any_value):
    return any_value


@pytest.fixture(params=[picobox.Box, picobox.ChainBox])
def boxclass(request):
    yield request.param
