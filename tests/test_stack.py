"""Test picobox's stack interface."""

import itertools
import traceback

import pytest
import picobox


def test_box_put_key(boxclass, supported_key):
    testbox = boxclass()

    with picobox.push(testbox):
        picobox.put(supported_key, 'the-value')

    assert testbox.get(supported_key) == 'the-value'


def test_box_put_value(boxclass, supported_value):
    testbox = boxclass()

    with picobox.push(testbox):
        picobox.put('the-key', supported_value)

    assert testbox.get('the-key') is supported_value


def test_box_put_factory(boxclass):
    testbox = boxclass()

    with picobox.push(testbox):
        picobox.put('the-key', factory=object)

    objects = [testbox.get('the-key') for _ in range(10)]

    assert len(objects) == 10
    assert len(set(map(id, objects))) == 10


def test_box_put_factory_singleton_scope(boxclass):
    testbox = boxclass()

    with picobox.push(testbox):
        picobox.put('the-key', factory=object, scope=picobox.singleton)

    objects = [testbox.get('the-key') for _ in range(10)]

    assert len(objects) == 10
    assert len(set(map(id, objects))) == 1


def test_box_put_factory_dependency(boxclass):
    testbox = boxclass()

    @picobox.pass_('a')
    def fn(a):
        return a + 1

    with picobox.push(testbox):
        picobox.put('a', 13)
        picobox.put('b', factory=fn)

        assert picobox.get('b') == 14


def test_box_put_value_and_factory(boxclass):
    testbox = boxclass()

    with picobox.push(testbox):
        with pytest.raises(ValueError) as excinfo:
            picobox.put('the-key', 42, factory=object)
    excinfo.match("either 'value' or 'factory'/'scope' pair must be passed")


def test_box_put_value_and_scope(boxclass):
    testbox = boxclass()

    with picobox.push(testbox):
        with pytest.raises(ValueError) as excinfo:
            picobox.put('the-key', 42, scope=picobox.threadlocal)
    excinfo.match("either 'value' or 'factory'/'scope' pair must be passed")


def test_box_put_runtimeerror(boxclass):
    with pytest.raises(RuntimeError) as excinfo:
        picobox.put('the-key', object())

    assert str(excinfo.value) == (
        'No boxes found on stack, please use picobox.push() first.')


def test_box_get_value(boxclass, supported_value):
    testbox = boxclass()
    testbox.put('the-key', supported_value)

    with picobox.push(testbox):
        assert picobox.get('the-key') is supported_value


def test_box_get_keyerror(boxclass):
    testbox = boxclass()

    with picobox.push(testbox):
        with pytest.raises(KeyError, match='the-key'):
            picobox.get('the-key')


def test_box_get_default(boxclass):
    testbox = boxclass()
    sentinel = object()

    with picobox.push(testbox):
        assert picobox.get('the-key', sentinel) is sentinel


@pytest.mark.parametrize('kwargs', [
    {},
    {'chain': False},
])
def test_box_get_from_top(boxclass, kwargs):
    testbox_a = boxclass()
    testbox_a.put('the-key', 'a')
    testbox_a.put('the-pin', 'a')

    testbox_b = boxclass()
    testbox_b.put('the-key', 'b')

    with picobox.push(testbox_a):
        assert picobox.get('the-key') == 'a'
        assert picobox.get('the-pin') == 'a'

        with picobox.push(testbox_b, **kwargs):
            assert picobox.get('the-key') == 'b'

            with pytest.raises(KeyError, match='the-pin'):
                picobox.get('the-pin')

        assert picobox.get('the-key') == 'a'
        assert picobox.get('the-pin') == 'a'


def test_box_get_from_top_chain(boxclass):
    testbox_a = boxclass()
    testbox_a.put('the-key', 'a')
    testbox_a.put('the-pin', 'a')

    testbox_b = boxclass()
    testbox_b.put('the-key', 'b')

    testbox_c = boxclass()
    testbox_c.put('the-tip', 'c')

    with picobox.push(testbox_a):
        assert picobox.get('the-key') == 'a'
        assert picobox.get('the-pin') == 'a'

        with picobox.push(testbox_b, chain=True):
            assert picobox.get('the-key') == 'b'
            assert picobox.get('the-pin') == 'a'

            with picobox.push(testbox_c, chain=True):
                assert picobox.get('the-tip') == 'c'
                assert picobox.get('the-key') == 'b'
                assert picobox.get('the-pin') == 'a'


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
def test_box_pass_a(args, kwargs, rv, boxclass):
    testbox = boxclass()
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
def test_box_pass_b(args, kwargs, rv, boxclass):
    testbox = boxclass()
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
def test_box_pass_c(args, kwargs, rv, boxclass):
    testbox = boxclass()
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
def test_box_pass_c_default(args, kwargs, rv, boxclass):
    testbox = boxclass()
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
def test_box_pass_ab(args, kwargs, rv, boxclass):
    testbox = boxclass()
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
def test_box_pass_bc(args, kwargs, rv, boxclass):
    testbox = boxclass()
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
def test_box_pass_ac(args, kwargs, rv, boxclass):
    testbox = boxclass()
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
def test_box_pass_abc(args, kwargs, rv, boxclass):
    testbox = boxclass()
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
def test_box_pass_d_as_b(args, kwargs, rv, boxclass):
    testbox = boxclass()
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
def test_box_pass_method(args, kwargs, rv, boxclass):
    testbox = boxclass()
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
def test_box_pass_key_type(args, kwargs, rv, boxclass):
    class key:
        pass

    testbox = boxclass()
    testbox.put(key, 1)

    @testbox.pass_(key, as_='x')
    def fn(x):
        return x + 41

    with picobox.push(testbox):
        assert fn(*args, **kwargs) == rv


def test_box_pass_unexpected_argument(boxclass):
    testbox = boxclass()
    testbox.put('d', 10)

    @picobox.pass_('d')
    def fn(a, b):
        return a + b

    with picobox.push(testbox):
        with pytest.raises(TypeError) as excinfo:
            fn(1, 2)

    assert str(excinfo.value) == "fn() got an unexpected keyword argument 'd'"


def test_box_pass_keyerror(boxclass):
    testbox = boxclass()

    @picobox.pass_('b')
    def fn(a, b):
        return a + b

    with picobox.push(testbox):
        with pytest.raises(KeyError, match='b'):
            fn(1)


def test_box_pass_optimization(boxclass, request):
    testbox = boxclass()
    testbox.put('a', 1)
    testbox.put('b', 1)
    testbox.put('d', 1)

    @picobox.pass_('a')
    @picobox.pass_('b')
    @picobox.pass_('d', as_='c')
    def fn(a, b, c):
        backtrace = list(itertools.dropwhile(
            lambda frame: frame[2] != request.function.__name__,
            traceback.extract_stack()))
        return backtrace[1:-1]

    with picobox.push(testbox):
        assert len(fn()) == 1


def test_box_pass_optimization_complex(boxclass, request):
    testbox = boxclass()
    testbox.put('a', 1)
    testbox.put('b', 1)
    testbox.put('c', 1)
    testbox.put('d', 1)

    def passthrough(fn):
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        return wrapper

    @picobox.pass_('a')
    @picobox.pass_('b')
    @passthrough
    @picobox.pass_('c')
    @picobox.pass_('d')
    def fn(a, b, c, d):
        backtrace = list(itertools.dropwhile(
            lambda frame: frame[2] != request.function.__name__,
            traceback.extract_stack()))
        return backtrace[1:-1]

    with picobox.push(testbox):
        assert len(fn()) == 3


def test_chainbox_put_changes_box():
    testbox = picobox.Box()
    testchainbox = picobox.ChainBox(testbox)

    with picobox.push(testchainbox):
        with pytest.raises(KeyError, match='the-key'):
            picobox.get('the-key')
        picobox.put('the-key', 42)

        assert testbox.get('the-key') == 42


def test_chainbox_get_chained():
    testbox_a = picobox.Box()
    testbox_a.put('the-key', 42)

    testbox_b = picobox.Box()
    testbox_b.put('the-key', 13)
    testbox_b.put('the-pin', 12)

    testchainbox = picobox.ChainBox(testbox_a, testbox_b)

    with picobox.push(testchainbox):
        assert testchainbox.get('the-key') == 42
        assert testchainbox.get('the-pin') == 12


def test_push_pop_as_regular_functions():
    @picobox.pass_('magic')
    def do(magic):
        return magic + 1

    foobox = picobox.Box()
    foobox.put('magic', 42)

    barbox = picobox.Box()
    barbox.put('magic', 13)

    picobox.push(foobox)
    assert do() == 43

    picobox.push(barbox)
    assert do() == 14

    assert picobox.pop() is barbox
    assert picobox.pop() is foobox


def test_pop_empty_stack():
    with pytest.raises(IndexError):
        picobox.pop()
