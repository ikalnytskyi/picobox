"""Box container."""

import functools
import inspect
import threading

from . import _scopes


# Missing is a special sentinel object that's used to indicate a value is
# missing when "None" is a valid input. It's important to define a human
# readable "__repr__" because its value is used in function signatures in
# API reference (see docs).
class _missing:
    def __repr__(self):
        return '<optional>'


_missing = _missing()


class Box(object):

    def __init__(self):
        self._store = {}
        self._scope_instances = {}
        self._lock = threading.Lock()

    def put(self, key, value=_missing, factory=_missing, scope=_missing):
        if value is not _missing \
                and (factory is not _missing or scope is not _missing):
            raise ValueError(
                "either 'value' or 'factory'/'scope' pair must be passed")

        # Value is a syntax sugar Box supports to store objects "As Is"
        # with singleton scope. In other words it's essentially the same
        # as one pass "factory=lambda: value". Alternatively, Box could
        # have just one factory argument and check it for callable, but
        # in this case it wouldn't support values which are callable by
        # its nature.
        if value is not _missing:
            def factory():
                return value
            scope = _scopes.singleton

        # If scope is not explicitly passed, Box assumes "No Scope"
        # scope which means each time someone asks a box to retrieve a
        # value it would use a factory function.
        elif scope is _missing:
            scope = _scopes.noscope

        # Convert a given scope class into a scope instance. Since key
        # is uniquely defined among all scopes within the same box, it's
        # safe to reuse already created scope instance in order to avoid
        # memory consumption when a lot of objects with the same scope
        # are put into a box.
        try:
            scope = self._scope_instances[scope]
        except KeyError:
            scope = self._scope_instances.setdefault(scope, scope())

        # Despite "dict" is thread-safe in CPython (due to GIL), it's not
        # guaranteed by the language itself and may not be the case among
        # alternative implementations.
        with self._lock:
            self._store[key] = (scope, factory)

    def get(self, key, default=_missing):
        # If nothing was put into a box under "key", Box follows mapping
        # interface and raises KeyError, unless some default value has been
        # passed as the fallback value.
        try:
            scope, factory = self._store[key]
        except KeyError:
            if default is _missing:
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

    def pass_(self, key, as_=_missing):
        def decorator(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                nonlocal as_

                if as_ is _missing:
                    as_ = key

                signature = inspect.signature(fn)
                arguments = signature.bind_partial(*args, **kwargs)

                # Box supplies an argument if and only if the argument wasn't
                # supplied explicitly by caller code. This is intended behavior
                # and a rationale behind is to preserve compatibility with
                # usual function call.
                if as_ not in arguments.arguments:
                    kwargs[as_] = self.get(key)

                return fn(*args, **kwargs)
            return wrapper
        return decorator
