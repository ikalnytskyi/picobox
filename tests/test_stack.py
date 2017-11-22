"""Test picobox's stack interface."""

import pytest
import picobox


@pytest.mark.parametrize('key', [
    42,
    '42',
    42.42,
    True,
    None,
    (1, None, True),
    object(),
])
def test_box_put_key(key):
    testbox = picobox.Box()

    with picobox.push(testbox):
        picobox.put(key, 'the-value')

    assert testbox.get(key) == 'the-value'


@pytest.mark.parametrize('value', [
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
def test_box_put_value(value):
    testbox = picobox.Box()

    with picobox.push(testbox):
        picobox.put('the-key', value)

    assert testbox.get('the-key') is value


def test_box_put_factory():
    testbox = picobox.Box()

    with picobox.push(testbox):
        picobox.put('the-key', factory=object)

    objects = [testbox.get('the-key') for _ in range(10)]

    assert len(objects) == 10
    assert len(set(map(id, objects))) == 10


def test_box_put_factory_singleton_scope():
    testbox = picobox.Box()

    with picobox.push(testbox):
        picobox.put('the-key', factory=object, scope=picobox.singleton)

    objects = [testbox.get('the-key') for _ in range(10)]

    assert len(objects) == 10
    assert len(set(map(id, objects))) == 1


def test_box_put_factory_dependency():
    testbox = picobox.Box()

    @picobox.pass_('a')
    def fn(a):
        return a + 1

    with picobox.push(testbox):
        picobox.put('a', 13)
        picobox.put('b', factory=fn)

        assert picobox.get('b') == 14


def test_box_put_value_and_factory():
    testbox = picobox.Box()

    with picobox.push(testbox):
        with pytest.raises(ValueError) as excinfo:
            picobox.put('the-key', 42, factory=object)
    excinfo.match("either 'value' or 'factory'/'scope' pair must be passed")


def test_box_put_value_and_scope():
    testbox = picobox.Box()

    with picobox.push(testbox):
        with pytest.raises(ValueError) as excinfo:
            picobox.put('the-key', 42, scope=picobox.threadlocal)
    excinfo.match("either 'value' or 'factory'/'scope' pair must be passed")


def test_box_put_runtimeerror():
    with pytest.raises(RuntimeError) as excinfo:
        picobox.put('the-key', object())

    assert str(excinfo.value) == (
        'No boxes found on stack, please use picobox.push() first.')


@pytest.mark.parametrize('value', [
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
def test_box_get_value(value):
    testbox = picobox.Box()
    testbox.put('the-key', value)

    with picobox.push(testbox):
        assert picobox.get('the-key') is value


def test_box_get_keyerror():
    testbox = picobox.Box()

    with picobox.push(testbox):
        with pytest.raises(KeyError) as excinfo:
            picobox.get('the-key')

    excinfo.match('the-key')


def test_box_get_default():
    testbox = picobox.Box()
    sentinel = object()

    with picobox.push(testbox):
        assert picobox.get('the-key', sentinel) is sentinel


def test_box_get_from_top():
    testbox_a = picobox.Box()
    testbox_b = picobox.Box()

    testbox_a.put('the-key', 'a')
    testbox_b.put('the-key', 'b')

    with picobox.push(testbox_a):
        assert picobox.get('the-key') == 'a'

        with picobox.push(testbox_b):
            assert picobox.get('the-key') == 'b'

        assert picobox.get('the-key') == 'a'


def test_box_get_runtimeerror():
    with pytest.raises(RuntimeError) as excinfo:
        picobox.get('the-key')

    assert str(excinfo.value) == (
        'No boxes found on stack, please use picobox.push() first.')


@pytest.mark.parametrize('args, kwargs, rv', [
    ((1, 2, 3),     {},                               6),
    ((1, 2),        {'c': 3},                         6),
    ((1,),          {'b': 2, 'c': 3},                 6),
    ((),            {'a': 1, 'b': 2, 'c': 3},         6),
    ((),            {'b': 2, 'c': 3},                15),
])
def test_box_pass_a(args, kwargs, rv):
    testbox = picobox.Box()
    testbox.put('a', 10)

    @picobox.pass_('a')
    def fn(a, b, c):
        return a + b + c

    with picobox.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize('args, kwargs, rv', [
    ((1, 2, 3),     {},                               6),
    ((1, 2),        {'c': 3},                         6),
    ((1,),          {'b': 2, 'c': 3},                 6),
    ((1,),          {'c': 3},                        14),
    ((),            {'a': 1, 'b': 2, 'c': 3},         6),
    ((),            {'a': 1, 'c': 3},                14),
])
def test_box_pass_b(args, kwargs, rv):
    testbox = picobox.Box()
    testbox.put('b', 10)

    @picobox.pass_('b')
    def fn(a, b, c):
        return a + b + c

    with picobox.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize('args, kwargs, rv', [
    ((1, 2, 3),     {},                               6),
    ((1, 2),        {'c': 3},                         6),
    ((1, 2),        {},                              13),
    ((1,),          {'b': 2, 'c': 3},                 6),
    ((1,),          {'b': 2},                        13),
    ((),            {'a': 1, 'b': 2, 'c': 3},         6),
    ((),            {'a': 1, 'b': 2},                13),
])
def test_box_pass_c(args, kwargs, rv):
    testbox = picobox.Box()
    testbox.put('c', 10)

    @picobox.pass_('c')
    def fn(a, b, c):
        return a + b + c

    with picobox.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize('args, kwargs, rv', [
    ((1, 2, 3),     {},                               6),
    ((1, 2),        {'c': 3},                         6),
    ((1, 2),        {},                              13),
    ((1,),          {'b': 2, 'c': 3},                 6),
    ((1,),          {'b': 2},                        13),
    ((),            {'a': 1, 'b': 2, 'c': 3},         6),
    ((),            {'a': 1, 'b': 2},                13),
])
def test_box_pass_c_default(args, kwargs, rv):
    testbox = picobox.Box()
    testbox.put('c', 10)

    @picobox.pass_('c')
    def fn(a, b, c=20):
        return a + b + c

    with picobox.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize('args, kwargs, rv', [
    ((1, 2, 3),     {},                               6),
    ((1, 2),        {'c': 3},                         6),
    ((1,),          {'b': 2, 'c': 3},                 6),
    ((1,),          {'c': 3},                       104),
    ((),            {'a': 1, 'b': 2, 'c': 3},         6),
    ((),            {'a': 1, 'c': 3},               104),
    ((),            {'b': 2, 'c': 3},                15),
    ((),            {'c': 3},                       113),
])
def test_box_pass_ab(args, kwargs, rv):
    testbox = picobox.Box()
    testbox.put('a', 10)
    testbox.put('b', 100)

    @picobox.pass_('a')
    @picobox.pass_('b')
    def fn(a, b, c):
        return a + b + c

    with picobox.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize('args, kwargs, rv', [
    ((1, 2, 3),     {},                               6),
    ((1, 2),        {'c': 3},                         6),
    ((1, 2),        {},                             103),
    ((1,),          {'b': 2, 'c': 3},                 6),
    ((1,),          {'b': 2},                       103),
    ((1,),          {'c': 3},                        14),
    ((1,),          {},                             111),
    ((),            {'a': 1, 'b': 2, 'c': 3},         6),
    ((),            {'a': 1, 'b': 2},               103),
    ((),            {'a': 1, 'c': 3},                14),
    ((),            {'a': 1},                       111),
])
def test_box_pass_bc(args, kwargs, rv):
    testbox = picobox.Box()
    testbox.put('b', 10)
    testbox.put('c', 100)

    @picobox.pass_('b')
    @picobox.pass_('c')
    def fn(a, b, c):
        return a + b + c

    with picobox.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize('args, kwargs, rv', [
    ((1, 2, 3),     {},                               6),
    ((1, 2),        {'c': 3},                         6),
    ((1, 2),        {},                             103),
    ((1,),          {'b': 2, 'c': 3},                 6),
    ((1,),          {'b': 2},                       103),
    ((),            {'a': 1, 'b': 2, 'c': 3},         6),
    ((),            {'a': 1, 'b': 2},               103),
    ((),            {'b': 2, 'c': 3},                15),
    ((),            {'b': 2},                       112),
])
def test_box_pass_ac(args, kwargs, rv):
    testbox = picobox.Box()
    testbox.put('a', 10)
    testbox.put('c', 100)

    @picobox.pass_('a')
    @picobox.pass_('c')
    def fn(a, b, c):
        return a + b + c

    with picobox.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize('args, kwargs, rv', [
    ((1, 2, 3),     {},                               6),
    ((1, 2),        {'c': 3},                         6),
    ((1, 2),        {},                            1003),
    ((1,),          {'b': 2, 'c': 3},                 6),
    ((1,),          {'b': 2},                      1003),
    ((1,),          {'c': 3},                       104),
    ((1,),          {},                            1101),
    ((),            {'a': 1, 'b': 2, 'c': 3},         6),
    ((),            {'a': 1, 'b': 2},              1003),
    ((),            {'a': 1, 'c': 3},               104),
    ((),            {'a': 1},                      1101),
    ((),            {},                            1110),
])
def test_box_pass_abc(args, kwargs, rv):
    testbox = picobox.Box()
    testbox.put('a', 10)
    testbox.put('b', 100)
    testbox.put('c', 1000)

    @picobox.pass_('a')
    @picobox.pass_('b')
    @picobox.pass_('c')
    def fn(a, b, c):
        return a + b + c

    with picobox.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize('args, kwargs, rv', [
    ((1, 2, 3),     {},                               6),
    ((1, 2),        {'c': 3},                         6),
    ((1,),          {'b': 2, 'c': 3},                 6),
    ((1,),          {'c': 3},                        14),
    ((),            {'a': 1, 'b': 2, 'c': 3},         6),
    ((),            {'a': 1, 'c': 3},                14),
])
def test_box_pass_d_as_b(args, kwargs, rv):
    testbox = picobox.Box()
    testbox.put('d', 10)

    @picobox.pass_('d', as_='b')
    def fn(a, b, c):
        return a + b + c

    with picobox.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize('args, kwargs, rv', [
    ((1, ),         {},                               1),
    ((),            {'x': 1},                         1),
    ((),            {},                              42),
])
def test_box_pass_method(args, kwargs, rv):
    testbox = picobox.Box()
    testbox.put('x', 42)

    class Foo:
        @picobox.pass_('x')
        def __init__(self, x):
            self.x = x

    with picobox.push(testbox):
        assert Foo(*args, **kwargs).x == rv


@pytest.mark.parametrize('args, kwargs, rv', [
    ((0, ),         {},                              41),
    ((),            {'x': 0},                        41),
    ((),            {},                              42),
])
def test_box_pass_key_type(args, kwargs, rv):
    class key:
        pass

    testbox = picobox.Box()
    testbox.put(key, 1)

    @testbox.pass_(key, as_='x')
    def fn(x):
        return x + 41

    with picobox.push(testbox):
        assert fn(*args, **kwargs) == rv


def test_box_pass_unexpected_argument():
    testbox = picobox.Box()
    testbox.put('d', 10)

    @picobox.pass_('d')
    def fn(a, b):
        return a + b

    with picobox.push(testbox):
        with pytest.raises(TypeError) as excinfo:
            fn(1, 2)

    assert str(excinfo.value) == "fn() got an unexpected keyword argument 'd'"


def test_box_pass_keyerror():
    testbox = picobox.Box()

    @picobox.pass_('b')
    def fn(a, b):
        return a + b

    with picobox.push(testbox):
        with pytest.raises(KeyError) as excinfo:
            fn(1)

    excinfo.match('b')
