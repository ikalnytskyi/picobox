"""Test picobox's stack interface."""

import itertools
import sys
import traceback

import pytest

import picobox


@pytest.fixture(params=[picobox.Stack(), picobox])
def teststack(request):
    return request.param


def test_box_put_key(boxclass, teststack, supported_key):
    testbox = boxclass()

    with teststack.push(testbox):
        teststack.put(supported_key, "the-value")

    assert testbox.get(supported_key) == "the-value"


def test_box_put_value(boxclass, teststack, supported_value):
    testbox = boxclass()

    with teststack.push(testbox):
        teststack.put("the-key", supported_value)

    assert testbox.get("the-key") is supported_value


def test_box_put_factory(boxclass, teststack):
    testbox = boxclass()

    with teststack.push(testbox):
        teststack.put("the-key", factory=object)

    objects = [testbox.get("the-key") for _ in range(10)]

    assert len(objects) == 10
    assert len(set(map(id, objects))) == 10


def test_box_put_factory_singleton_scope(boxclass, teststack):
    testbox = boxclass()

    with teststack.push(testbox):
        teststack.put("the-key", factory=object, scope=picobox.singleton)

    objects = [testbox.get("the-key") for _ in range(10)]

    assert len(objects) == 10
    assert len(set(map(id, objects))) == 1


def test_box_put_factory_dependency(boxclass, teststack):
    testbox = boxclass()

    @teststack.pass_("a")
    def fn(a):
        return a + 1

    with teststack.push(testbox):
        teststack.put("a", 13)
        teststack.put("b", factory=fn)

        assert teststack.get("b") == 14


def test_box_put_value_factory_required(boxclass, teststack):
    testbox = boxclass()

    with teststack.push(testbox):
        with pytest.raises(TypeError) as excinfo:
            teststack.put("the-key")

    assert str(excinfo.value) == (
        "Box.put() missing 1 required argument: either 'value' or 'factory'"
    )


def test_box_put_value_and_factory(boxclass, teststack):
    testbox = boxclass()

    with teststack.push(testbox):
        with pytest.raises(TypeError) as excinfo:
            teststack.put("the-key", 42, factory=object)

    assert str(excinfo.value) == "Box.put() takes either 'value' or 'factory', not both"


def test_box_put_value_and_scope(boxclass, teststack):
    testbox = boxclass()

    with teststack.push(testbox):
        with pytest.raises(TypeError) as excinfo:
            teststack.put("the-key", 42, scope=picobox.threadlocal)

    assert str(excinfo.value) == "Box.put() takes 'scope' when 'factory' provided"


def test_box_put_runtimeerror(boxclass, teststack):
    with pytest.raises(RuntimeError) as excinfo:
        teststack.put("the-key", object())

    assert str(excinfo.value) == "No boxes found on the stack, please `.push()` a box first."


def test_box_get_value(boxclass, teststack, supported_value):
    testbox = boxclass()
    testbox.put("the-key", supported_value)

    with teststack.push(testbox):
        assert teststack.get("the-key") is supported_value


def test_box_get_keyerror(boxclass, teststack):
    testbox = boxclass()

    with teststack.push(testbox):
        with pytest.raises(KeyError, match="the-key"):
            teststack.get("the-key")


def test_box_get_default(boxclass, teststack):
    testbox = boxclass()
    sentinel = object()

    with teststack.push(testbox):
        assert teststack.get("the-key", sentinel) is sentinel


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"chain": False},
    ],
)
def test_box_get_from_top(boxclass, teststack, kwargs):
    testbox_a = boxclass()
    testbox_a.put("the-key", "a")
    testbox_a.put("the-pin", "a")

    testbox_b = boxclass()
    testbox_b.put("the-key", "b")

    with teststack.push(testbox_a):
        assert teststack.get("the-key") == "a"
        assert teststack.get("the-pin") == "a"

        with teststack.push(testbox_b, **kwargs):
            assert teststack.get("the-key") == "b"

            with pytest.raises(KeyError, match="the-pin"):
                teststack.get("the-pin")

        assert teststack.get("the-key") == "a"
        assert teststack.get("the-pin") == "a"


def test_box_get_from_top_chain(boxclass, teststack):
    testbox_a = boxclass()
    testbox_a.put("the-key", "a")
    testbox_a.put("the-pin", "a")

    testbox_b = boxclass()
    testbox_b.put("the-key", "b")

    testbox_c = boxclass()
    testbox_c.put("the-tip", "c")

    with teststack.push(testbox_a):
        assert teststack.get("the-key") == "a"
        assert teststack.get("the-pin") == "a"

        with teststack.push(testbox_b, chain=True):
            assert teststack.get("the-key") == "b"
            assert teststack.get("the-pin") == "a"

            with teststack.push(testbox_c, chain=True):
                assert teststack.get("the-tip") == "c"
                assert teststack.get("the-key") == "b"
                assert teststack.get("the-pin") == "a"


def test_box_get_runtimeerror(teststack):
    with pytest.raises(RuntimeError) as excinfo:
        teststack.get("the-key")

    assert str(excinfo.value) == "No boxes found on the stack, please `.push()` a box first."


@pytest.mark.parametrize(
    ("args", "kwargs", "rv"),
    [
        ((1, 2, 3), {}, 6),
        ((1, 2), {"c": 3}, 6),
        ((1,), {"b": 2, "c": 3}, 6),
        ((), {"a": 1, "b": 2, "c": 3}, 6),
        ((), {"b": 2, "c": 3}, 15),
    ],
)
def test_box_pass_a(boxclass, teststack, args, kwargs, rv):
    testbox = boxclass()
    testbox.put("a", 10)

    @teststack.pass_("a")
    def fn(a, b, c):
        return a + b + c

    with teststack.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize(
    ("args", "kwargs", "rv"),
    [
        ((1, 2, 3), {}, 6),
        ((1, 2), {"c": 3}, 6),
        ((1,), {"b": 2, "c": 3}, 6),
        ((1,), {"c": 3}, 14),
        ((), {"a": 1, "b": 2, "c": 3}, 6),
        ((), {"a": 1, "c": 3}, 14),
    ],
)
def test_box_pass_b(boxclass, teststack, args, kwargs, rv):
    testbox = boxclass()
    testbox.put("b", 10)

    @teststack.pass_("b")
    def fn(a, b, c):
        return a + b + c

    with teststack.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize(
    ("args", "kwargs", "rv"),
    [
        ((1, 2, 3), {}, 6),
        ((1, 2), {"c": 3}, 6),
        ((1, 2), {}, 13),
        ((1,), {"b": 2, "c": 3}, 6),
        ((1,), {"b": 2}, 13),
        ((), {"a": 1, "b": 2, "c": 3}, 6),
        ((), {"a": 1, "b": 2}, 13),
    ],
)
def test_box_pass_c(boxclass, teststack, args, kwargs, rv):
    testbox = boxclass()
    testbox.put("c", 10)

    @teststack.pass_("c")
    def fn(a, b, c):
        return a + b + c

    with teststack.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize(
    ("args", "kwargs", "rv"),
    [
        ((1, 2, 3), {}, 6),
        ((1, 2), {"c": 3}, 6),
        ((1, 2), {}, 13),
        ((1,), {"b": 2, "c": 3}, 6),
        ((1,), {"b": 2}, 13),
        ((), {"a": 1, "b": 2, "c": 3}, 6),
        ((), {"a": 1, "b": 2}, 13),
    ],
)
def test_box_pass_c_default(boxclass, teststack, args, kwargs, rv):
    testbox = boxclass()
    testbox.put("c", 10)

    @teststack.pass_("c")
    def fn(a, b, c=20):
        return a + b + c

    with teststack.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize(
    ("args", "kwargs", "rv"),
    [
        ((1, 2, 3), {}, 6),
        ((1, 2), {"c": 3}, 6),
        ((1,), {"b": 2, "c": 3}, 6),
        ((1,), {"c": 3}, 104),
        ((), {"a": 1, "b": 2, "c": 3}, 6),
        ((), {"a": 1, "c": 3}, 104),
        ((), {"b": 2, "c": 3}, 15),
        ((), {"c": 3}, 113),
    ],
)
def test_box_pass_ab(boxclass, teststack, args, kwargs, rv):
    testbox = boxclass()
    testbox.put("a", 10)
    testbox.put("b", 100)

    @teststack.pass_("a")
    @teststack.pass_("b")
    def fn(a, b, c):
        return a + b + c

    with teststack.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize(
    ("args", "kwargs", "rv"),
    [
        ((1, 2, 3), {}, 6),
        ((1, 2), {"c": 3}, 6),
        ((1, 2), {}, 103),
        ((1,), {"b": 2, "c": 3}, 6),
        ((1,), {"b": 2}, 103),
        ((1,), {"c": 3}, 14),
        ((1,), {}, 111),
        ((), {"a": 1, "b": 2, "c": 3}, 6),
        ((), {"a": 1, "b": 2}, 103),
        ((), {"a": 1, "c": 3}, 14),
        ((), {"a": 1}, 111),
    ],
)
def test_box_pass_bc(boxclass, teststack, args, kwargs, rv):
    testbox = boxclass()
    testbox.put("b", 10)
    testbox.put("c", 100)

    @teststack.pass_("b")
    @teststack.pass_("c")
    def fn(a, b, c):
        return a + b + c

    with teststack.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize(
    ("args", "kwargs", "rv"),
    [
        ((1, 2, 3), {}, 6),
        ((1, 2), {"c": 3}, 6),
        ((1, 2), {}, 103),
        ((1,), {"b": 2, "c": 3}, 6),
        ((1,), {"b": 2}, 103),
        ((), {"a": 1, "b": 2, "c": 3}, 6),
        ((), {"a": 1, "b": 2}, 103),
        ((), {"b": 2, "c": 3}, 15),
        ((), {"b": 2}, 112),
    ],
)
def test_box_pass_ac(boxclass, teststack, args, kwargs, rv):
    testbox = boxclass()
    testbox.put("a", 10)
    testbox.put("c", 100)

    @teststack.pass_("a")
    @teststack.pass_("c")
    def fn(a, b, c):
        return a + b + c

    with teststack.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize(
    ("args", "kwargs", "rv"),
    [
        ((1, 2, 3), {}, 6),
        ((1, 2), {"c": 3}, 6),
        ((1, 2), {}, 1003),
        ((1,), {"b": 2, "c": 3}, 6),
        ((1,), {"b": 2}, 1003),
        ((1,), {"c": 3}, 104),
        ((1,), {}, 1101),
        ((), {"a": 1, "b": 2, "c": 3}, 6),
        ((), {"a": 1, "b": 2}, 1003),
        ((), {"a": 1, "c": 3}, 104),
        ((), {"a": 1}, 1101),
        ((), {}, 1110),
    ],
)
def test_box_pass_abc(boxclass, teststack, args, kwargs, rv):
    testbox = boxclass()
    testbox.put("a", 10)
    testbox.put("b", 100)
    testbox.put("c", 1000)

    @teststack.pass_("a")
    @teststack.pass_("b")
    @teststack.pass_("c")
    def fn(a, b, c):
        return a + b + c

    with teststack.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize(
    ("args", "kwargs", "rv"),
    [
        ((1, 2, 3), {}, 6),
        ((1, 2), {"c": 3}, 6),
        ((1,), {"b": 2, "c": 3}, 6),
        ((1,), {"c": 3}, 14),
        ((), {"a": 1, "b": 2, "c": 3}, 6),
        ((), {"a": 1, "c": 3}, 14),
    ],
)
def test_box_pass_d_as_b(boxclass, teststack, args, kwargs, rv):
    testbox = boxclass()
    testbox.put("d", 10)

    @teststack.pass_("d", as_="b")
    def fn(a, b, c):
        return a + b + c

    with teststack.push(testbox):
        assert fn(*args, **kwargs) == rv


@pytest.mark.parametrize(
    ("args", "kwargs", "rv"),
    [
        ((1,), {}, 1),
        ((), {"x": 1}, 1),
        ((), {}, 42),
    ],
)
def test_box_pass_method(boxclass, teststack, args, kwargs, rv):
    testbox = boxclass()
    testbox.put("x", 42)

    class Foo:
        @teststack.pass_("x")
        def __init__(self, x):
            self.x = x

    with teststack.push(testbox):
        assert Foo(*args, **kwargs).x == rv


@pytest.mark.parametrize(
    ("args", "kwargs", "rv"),
    [
        ((0,), {}, 41),
        ((), {"x": 0}, 41),
        ((), {}, 42),
    ],
)
def test_box_pass_key_type(boxclass, teststack, args, kwargs, rv):
    class key:
        pass

    testbox = boxclass()
    testbox.put(key, 1)

    @testbox.pass_(key, as_="x")
    def fn(x):
        return x + 41

    with teststack.push(testbox):
        assert fn(*args, **kwargs) == rv


def test_box_pass_unexpected_argument(boxclass, teststack):
    testbox = boxclass()
    testbox.put("d", 10)

    @teststack.pass_("d")
    def fn(a, b):
        return a + b

    with teststack.push(testbox):
        with pytest.raises(TypeError) as excinfo:
            fn(1, 2)

    expected = "fn() got an unexpected keyword argument 'd'"
    if sys.version_info >= (3, 10):
        expected = f"test_box_pass_unexpected_argument.<locals>.{expected}"

    assert str(excinfo.value) == expected


def test_box_pass_keyerror(boxclass, teststack):
    testbox = boxclass()

    @teststack.pass_("b")
    def fn(a, b):
        return a + b

    with teststack.push(testbox):
        with pytest.raises(KeyError, match="b"):
            fn(1)


def test_box_pass_runtimeerror(teststack):
    @teststack.pass_("a")
    def fn(a):
        return a

    with pytest.raises(RuntimeError) as excinfo:
        fn()

    assert str(excinfo.value) == "No boxes found on the stack, please `.push()` a box first."


def test_box_pass_optimization(boxclass, teststack, request):
    testbox = boxclass()
    testbox.put("a", 1)
    testbox.put("b", 1)
    testbox.put("d", 1)

    @teststack.pass_("a")
    @teststack.pass_("b")
    @teststack.pass_("d", as_="c")
    def fn(a, b, c):
        backtrace = list(
            itertools.dropwhile(
                lambda frame: frame[2] != request.function.__name__,
                traceback.extract_stack(),
            )
        )
        return backtrace[1:-1]

    with teststack.push(testbox):
        assert len(fn()) == 1


def test_box_pass_optimization_complex(boxclass, teststack, request):
    testbox = boxclass()
    testbox.put("a", 1)
    testbox.put("b", 1)
    testbox.put("c", 1)
    testbox.put("d", 1)

    def passthrough(fn):
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        return wrapper

    @teststack.pass_("a")
    @teststack.pass_("b")
    @passthrough
    @teststack.pass_("c")
    @teststack.pass_("d")
    def fn(a, b, c, d):
        backtrace = list(
            itertools.dropwhile(
                lambda frame: frame[2] != request.function.__name__,
                traceback.extract_stack(),
            )
        )
        return backtrace[1:-1]

    with teststack.push(testbox):
        assert len(fn()) == 3


def test_chainbox_put_changes_box(teststack):
    testbox = picobox.Box()
    testchainbox = picobox.ChainBox(testbox)

    with teststack.push(testchainbox):
        with pytest.raises(KeyError, match="the-key"):
            teststack.get("the-key")
        teststack.put("the-key", 42)

        assert testbox.get("the-key") == 42


def test_chainbox_get_chained(teststack):
    testbox_a = picobox.Box()
    testbox_a.put("the-key", 42)

    testbox_b = picobox.Box()
    testbox_b.put("the-key", 13)
    testbox_b.put("the-pin", 12)

    testchainbox = picobox.ChainBox(testbox_a, testbox_b)

    with teststack.push(testchainbox):
        assert testchainbox.get("the-key") == 42
        assert testchainbox.get("the-pin") == 12


def test_stack_isolated(boxclass):
    testbox_a = picobox.Box()
    testbox_a.put("the-key", 42)

    testbox_b = picobox.Box()
    testbox_b.put("the-pin", 12)

    teststack_a = picobox.Stack()
    teststack_b = picobox.Stack()

    with teststack_a.push(testbox_a):
        with pytest.raises(RuntimeError) as excinfo:
            teststack_b.get("the-key")
        assert str(excinfo.value) == "No boxes found on the stack, please `.push()` a box first."

        with teststack_b.push(testbox_b):
            with pytest.raises(KeyError, match="the-pin"):
                teststack_a.get("the-pin")
            assert teststack_b.get("the-pin") == 12


def test_push_pop_as_regular_functions(teststack):
    @teststack.pass_("magic")
    def do(magic):
        return magic + 1

    foobox = picobox.Box()
    foobox.put("magic", 42)

    barbox = picobox.Box()
    barbox.put("magic", 13)

    teststack.push(foobox)
    assert do() == 43

    teststack.push(barbox)
    assert do() == 14

    assert teststack.pop() is barbox
    assert teststack.pop() is foobox


def test_pop_empty_stack(teststack):
    with pytest.raises(IndexError):
        teststack.pop()
