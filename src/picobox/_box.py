"""Box container."""

from __future__ import annotations

import functools
import inspect
import threading
import typing

from . import _scopes


if typing.TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Hashable
    from typing import Any, ParamSpec, TypeVar, Union

    P = ParamSpec("P")
    T = TypeVar("T")
    R = Union[T, Awaitable[T]]

# Missing is a special sentinel object that's used to indicate a value is
# missing when "None" is a valid input. It's important to use a good name
# because it appears in function signatures in API reference (see docs).
_unset = object()


class Box:
    """Box is a dependency injection (DI) container.

    DI container is an object that contains any amount of factories, one for
    each dependency apart. Dependency, on the other hand, is an ordinary
    instance or value the container needs to provide on demand.

    Thanks to scopes, the class keeps track of produced dependencies and knows
    exactly when to reuse them or when to create new ones. That is to say each
    scope defines a set of rules for when to reuse dependencies.

    Here's a minimal example of how a Box instance can be used::

        import picobox

        box = picobox.Box()
        box.put('magic', 42)

        @box.pass_('magic')
        def do(magic):
            return magic + 1

        assert box.get('magic') == 42
        assert do(13) == 14
        assert do() == 43
    """

    def __init__(self) -> None:
        self._store: dict[Hashable, tuple[_scopes.Scope, Callable[[], Any]]] = {}
        self._scope_instances: dict[type[_scopes.Scope], _scopes.Scope] = {}
        self._lock = threading.RLock()

    def put(
        self,
        key: Hashable,
        value: Any = _unset,
        *,
        factory: Callable[[], Any] | None = None,
        scope: type[_scopes.Scope] | None = None,
    ) -> None:
        """Define a dependency (aka service) within the box instance.

        A dependency can be expressed either directly, by passing a concrete
        `value`, or via `factory` function. A `factory` may be accompanied by
        `scope` that defines a set of rules for when to create a new dependency
        instance and when to reuse existing one. If `scope` is not passed, no
        scope is assumed which means produce a new instance each time it's
        requested.

        :param key: A key under which to put a dependency. Can be any hashable
            object, but string is recommended.
        :param value: A dependency to be stored within a box under `key` key.
            Can be any object. A syntax sugar for ``factory=lambda: value``.
        :param factory: A factory function to produce a dependency when needed.
            Must be callable with no arguments.
        :param scope: A scope to keep track of produced dependencies. Must be
            a class that implements :class:`Scope` interface.
        :raises ValueError: If both `value` and `factory` are passed.
        """
        if value is _unset and factory is None:
            error_message = "Box.put() missing 1 required argument: either 'value' or 'factory'"
            raise TypeError(error_message)

        if value is not _unset and factory is not None:
            error_message = "Box.put() takes either 'value' or 'factory', not both"
            raise TypeError(error_message)

        if value is not _unset and scope is not None:
            error_message = "Box.put() takes 'scope' when 'factory' provided"
            raise TypeError(error_message)

        def _factory() -> Any:
            return value

        factory = factory or _factory

        # Value is a syntax sugar Box supports to store objects "As Is"
        # with singleton scope. In other words it's essentially the same
        # as one pass "factory=lambda: value". Alternatively, Box could
        # have just one factory argument and check it for callable, but
        # in this case it wouldn't support values which are callable by
        # its nature.
        if value is not _unset:
            scope = _scopes.singleton

        # If scope is not explicitly passed, Box assumes "No Scope"
        # scope which means each time someone asks a box to retrieve a
        # value it would use a factory function.
        elif scope is None:
            scope = _scopes.noscope

        # Convert a given scope class into a scope instance. Since key
        # is uniquely defined among all scopes within the same box, it's
        # safe to reuse already created scope instance in order to avoid
        # memory consumption when a lot of objects with the same scope
        # are put into a box.
        try:
            scope_instance = self._scope_instances[scope]
        except KeyError:
            scope_instance = self._scope_instances.setdefault(scope, scope())

        # Despite "dict" is thread-safe in CPython (due to GIL), it's not
        # guaranteed by the language itself and may not be the case among
        # alternative implementations.
        with self._lock:
            self._store[key] = (scope_instance, factory)

    def get(self, key: Hashable, default: Any = _unset) -> Any:
        """Retrieve a dependency (aka service) out of the box instance.

        The process involves creation of requested dependency by calling an
        associated `factory` function, and then returning result back to the
        caller code. If a dependency is `scoped`, there's a chance for an
        existing instance to be returned instead.

        :param key: A key to retrieve a dependency. Must be the one used when
            calling :meth:`.put` method.
        :param default: (optional) A fallback value to be returned if there's
            no `key` in the box. If not passed, `KeyError` is raised.
        :raises KeyError: If no dependencies saved under `key` in the box.
        """
        # If nothing was put into a box under "key", Box follows mapping
        # interface and raises KeyError, unless some default value has been
        # passed as the fallback value.
        try:
            scope, factory = self._store[key]
        except KeyError:
            if default is _unset:
                raise
            return default

        # If something was put into a box under "key", Box tries to retrieve a
        # value. If it does not exist for current execution context, Box uses a
        # factory function to create one. For implementation details below
        # please refer to double-checked locking design pattern.
        try:
            value = scope.get(key)
        except KeyError:
            with self._lock:
                try:
                    value = scope.get(key)
                except KeyError:
                    value = factory()
                    scope.set(key, value)

        return value

    def pass_(
        self,
        key: Hashable,
        *,
        as_: str | None = None,
    ) -> Callable[[Callable[P, R[T]]], Callable[P, R[T]]]:
        r"""Pass a dependency to a function if nothing explicitly passed.

        The decorator implements late binding which means it does not require
        to have a dependency instance in the box before applying. The instance
        will be looked up when a decorated function is called. Other important
        property is that it doesn't change a signature of decorated function
        preserving a way to explicitly pass arguments ignoring injections.

        :param key: A key to retrieve a dependency. Must be the one used when
            calling :meth:`.put` method.
        :param as\_: (optional) Bind a dependency associated with `key` to
            a function argument named `as_`. If not passed, the same as `key`.
        :raises KeyError: If no dependencies saved under `key` in the box.
        """

        def decorator(fn: Callable[P, R[T]]) -> Callable[P, R[T]]:
            # If pass_ decorator is called second time (or more), we can squash
            # the calls into one and reduce runtime costs of injection.
            if hasattr(fn, "__dependencies__"):
                fn.__dependencies__.append((key, as_))
                return fn

            @functools.wraps(fn)
            def fn_with_dependencies(*args: P.args, **kwargs: P.kwargs) -> R[T]:
                signature = inspect.signature(fn)
                arguments = signature.bind_partial(*args, **kwargs)

                for key, as_ in wrapper.__dependencies__:  # type: ignore[attr-defined]
                    if as_ is None:
                        as_ = key

                    # One of picobox core principles is to supply dependencies
                    # if and only if they weren't passed explicitly by the
                    # caller code. A rationale behind is to be compatible with
                    # calls written prior picobox integration.
                    if as_ not in arguments.arguments:
                        kwargs[as_] = self.get(key)
                return fn(*args, **kwargs)

            if inspect.iscoroutinefunction(fn):

                @functools.wraps(fn)
                async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                    coroutine = fn_with_dependencies(*args, **kwargs)
                    return await typing.cast(typing.Awaitable["T"], coroutine)
            else:
                wrapper = fn_with_dependencies  # type: ignore[assignment]

            wrapper.__dependencies__ = [(key, as_)]  # type: ignore[attr-defined]
            return wrapper

        return decorator


class ChainBox(Box):
    """ChainBox groups multiple boxes together to create a single view.

    ChainBox for boxes is essentially the same as
    :class:`~collections.ChainMap` for mappings. It mimics :class:`Box`
    interface and hence can substitute one but provides a way to look up
    dependencies in underlying boxes.

    Here's a minimal example of how ChainBox instance can be used::

        box_a = picobox.Box()
        box_a.put('magic_a', 42)

        box_b = picobox.Box()
        box_b.put('magic_a', factory=lambda: 10)
        box_b.put('magic_b', factory=lambda: 13)

        chainbox = picobox.ChainBox(box_a, box_b)

        @chainbox.pass_('magic_a')
        @chainbox.pass_('magic_b')
        def do(magic_a, magic_b):
            return magic_a + magic_b

        assert chainbox.get('magic_b') == 13
        assert do() == 55

    :param boxes: (optional) A list of boxes to lookup into. If no boxes are
        passed, an empty box is created and used as underlying box instead.

    .. versionadded:: 1.1
    """

    def __init__(self, *boxes: Box) -> None:
        self._boxes = boxes or (Box(),)

    def put(
        self,
        key: Hashable,
        value: Any = _unset,
        *,
        factory: Callable[[], Any] | None = None,
        scope: type[_scopes.Scope] | None = None,
    ) -> None:
        """Same as :meth:`Box.put` but applies to first underlying box."""
        return self._boxes[0].put(key, value, factory=factory, scope=scope)

    def get(self, key: Hashable, default: Any = _unset) -> Any:
        """Same as :meth:`Box.get` but looks up for key in underlying boxes."""
        for box in self._boxes:
            try:
                return box.get(key)
            except KeyError:
                pass

        if default is _unset:
            raise KeyError(key)
        return default
