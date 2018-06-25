"""Test picobox class."""

import collections
import inspect
import itertools
import traceback

import pytest
import picobox

from picobox import _compat


def test_box_put_key(boxclass, supported_key):
    testbox = boxclass()
    testbox.put(supported_key, 'the-value')

    assert testbox.get(supported_key) == 'the-value'


def test_box_put_value(boxclass, supported_value):
    testbox = boxclass()
    testbox.put('the-key', supported_value)

    assert testbox.get('the-key') is supported_value


def test_box_put_factory(boxclass):
    testbox = boxclass()
    testbox.put('the-key', factory=object)

    objects = [testbox.get('the-key') for _ in range(10)]

    assert len(objects) == 10
    assert len(set(map(id, objects))) == 10


def test_box_put_factory_singleton_scope(boxclass):
    testbox = boxclass()
    testbox.put('the-key', factory=object, scope=picobox.singleton)

    objects = [testbox.get('the-key') for _ in range(10)]

    assert len(objects) == 10
    assert len(set(map(id, objects))) == 1


def test_box_put_factory_custom_scope(boxclass):
    class namespacescope(picobox.Scope):

        def __init__(self):
            self._store = collections.defaultdict(dict)

        def set(self, key, value):
            self._store[namespace][key] = value

        def get(self, key):
            return self._store[namespace][key]

    testbox = boxclass()
    testbox.put('the-key', factory=object, scope=namespacescope)

    objects = []

    namespace = 'one'
    objects.extend([
        testbox.get('the-key'),
        testbox.get('the-key'),
    ])

    namespace = 'two'
    objects.extend([
        testbox.get('the-key'),
        testbox.get('the-key'),
    ])

    assert len(objects) == 4
    assert len(set(map(id, objects[:2]))) == 1
    assert len(set(map(id, objects[2:]))) == 1
    assert len(set(map(id, objects))) == 2


def test_box_put_factory_dependency(boxclass):
    testbox = boxclass()

    @testbox.pass_('a')
    def fn(a):
        return a + 1

    testbox.put('a', 13)
    testbox.put('b', factory=fn)

    assert testbox.get('b') == 14


def test_box_put_value_and_factory(boxclass):
    testbox = boxclass()

    with pytest.raises(ValueError) as excinfo:
        testbox.put('the-key', 42, factory=object)
    excinfo.match("either 'value' or 'factory'/'scope' pair must be passed")


def test_box_put_value_and_scope(boxclass):
    testbox = boxclass()

    with pytest.raises(ValueError) as excinfo:
        testbox.put('the-key', 42, scope=picobox.threadlocal)
    excinfo.match("either 'value' or 'factory'/'scope' pair must be passed")


def test_box_get_keyerror(boxclass):
    testbox = boxclass()

    with pytest.raises(KeyError, match='the-key'):
        testbox.get('the-key')


def test_box_get_default(boxclass):
    testbox = boxclass()
    sentinel = object()

    assert testbox.get('the-key', sentinel) is sentinel


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

    @testbox.pass_('a')
    def fn(a, b, c):
        return a + b + c

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

    @testbox.pass_('b')
    def fn(a, b, c):
        return a + b + c

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

    @testbox.pass_('c')
    def fn(a, b, c):
        return a + b + c

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

    @testbox.pass_('c')
    def fn(a, b, c=20):
        return a + b + c

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

    @testbox.pass_('a')
    @testbox.pass_('b')
    def fn(a, b, c):
        return a + b + c

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

    @testbox.pass_('b')
    @testbox.pass_('c')
    def fn(a, b, c):
        return a + b + c

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

    @testbox.pass_('a')
    @testbox.pass_('c')
    def fn(a, b, c):
        return a + b + c

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

    @testbox.pass_('a')
    @testbox.pass_('b')
    @testbox.pass_('c')
    def fn(a, b, c):
        return a + b + c

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

    @testbox.pass_('d', as_='b')
    def fn(a, b, c):
        return a + b + c

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
        @testbox.pass_('x')
        def __init__(self, x):
            self.x = x

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

    assert fn(*args, **kwargs) == rv


def test_box_pass_unexpected_argument(boxclass):
    testbox = boxclass()
    testbox.put('d', 10)

    @testbox.pass_('d')
    def fn(a, b):
        return a + b

    with pytest.raises(TypeError) as excinfo:
        fn(1, 2)

    assert str(excinfo.value) == "fn() got an unexpected keyword argument 'd'"


def test_box_pass_keyerror(boxclass):
    testbox = boxclass()

    @testbox.pass_('b')
    def fn(a, b):
        return a + b

    with pytest.raises(KeyError) as excinfo:
        fn(1)

    excinfo.match('b')


def test_box_pass_optimization(boxclass, request):
    testbox = boxclass()
    testbox.put('a', 1)
    testbox.put('b', 1)
    testbox.put('d', 1)

    @testbox.pass_('a')
    @testbox.pass_('b')
    @testbox.pass_('d', as_='c')
    def fn(a, b, c):
        backtrace = list(itertools.dropwhile(
            lambda frame: frame[2] != request.function.__name__,
            traceback.extract_stack()))
        return backtrace[1:-1]

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

    @testbox.pass_('a')
    @testbox.pass_('b')
    @passthrough
    @testbox.pass_('c')
    @testbox.pass_('d')
    def fn(a, b, c, d):
        backtrace = list(itertools.dropwhile(
            lambda frame: frame[2] != request.function.__name__,
            traceback.extract_stack()))
        return backtrace[1:-1]

    assert len(fn()) == 3


def test_chainbox_put_changes_box():
    testbox = picobox.Box()
    testchainbox = picobox.ChainBox(testbox)

    with pytest.raises(KeyError, match='the-key'):
        testchainbox.get('the-key')
    testchainbox.put('the-key', 42)

    assert testbox.get('the-key') == 42


def test_chainbox_get_chained():
    testbox_a = picobox.Box()
    testbox_a.put('the-key', 42)

    testbox_b = picobox.Box()
    testbox_b.put('the-key', 13)
    testbox_b.put('the-pin', 12)

    testchainbox = picobox.ChainBox(testbox_a, testbox_b)

    assert testchainbox.get('the-key') == 42
    assert testchainbox.get('the-pin') == 12


def test_chainbox_isinstance_box():
    assert isinstance(picobox.ChainBox(), picobox.Box)


@pytest.mark.parametrize('name', [
    name
    for name, _ in inspect.getmembers(picobox.Box) if not name.startswith('_')
])
def test_chainbox_box_interface(name):
    boxsignature = _compat.signature(getattr(picobox.Box(), name))
    chainboxsignature = _compat.signature(getattr(picobox.ChainBox(), name))

    assert boxsignature == chainboxsignature
