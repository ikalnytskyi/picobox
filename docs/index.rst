Picobox
=======

Picobox is opinionated `dependency injection`__ framework designed to be clean,
pragmatic and with Python in mind. No complex graphs, no implicit injections,
no type bindings, no XML configurations.

.. __: https://en.wikipedia.org/wiki/Dependency_injection


Why?
----

Dependency Injection (DI) design pattern is intended to decouple various parts
of an application from each other. So a class can be independent of how the
objects it requires are created, and hence the way we create them may be
different for production and tests.

One of the most easiest examples is to say that DI is essentially about writing

.. code:: python

    def do_something(my_service):
        return my_service.get_val() + 42


    my_service = MyService(foo, bar)
    do_something(my_service)

instead of

.. code:: python

    def do_something():
        my_service = MyService(foo, bar)
        return my_service.get_val() + 42


    do_something()

because the latter is considered non-configurable and is harder to test.

In Python, however, dependency injection is not a big deal due to its dynamic
nature and duck typing: anything could be defined anytime and passed anywhere.
Due to that reason (and maybe some others) DI frameworks aren't popular among
Python community, though they may be handy in some cases.

One of such cases is code decoupling when we want to create and use objects in
different places, preserving clean interface and avoiding global variables.
Having all these considerations in mind, Picobox was born.


Quickstart
----------

Picobox provides ``Box`` class that acts as a container for objects you want
to deal with. You can put, you can get, you can pass them around.

.. code:: python

    import picobox

    box = picobox.Box()
    box.put("foo", 42)


    @box.pass_("foo")
    def spam(foo):
        return foo


    @box.pass_("foo", as_="bar")
    def eggs(bar):
        return bar


    print(box.get("foo"))   # ==> 42
    print(spam())           # ==> 42
    print(eggs())           # ==> 42

One of the key principles is `not to break` existing code. That's why Picobox
does not change function signature and injects dependencies as if they are
defaults.

.. code:: python

    print(spam())           # ==> 42
    print(spam(13))         # ==> 13
    print(spam(foo=99))     # ==> 99

Another key principle is that ``pass_()`` resolves dependencies lazily which
means you can inject them everywhere you need and define them much later. The
only rule is to define them before calling the function.

.. code:: python

    import picobox

    box = picobox.Box()


    @box.pass_("foo")
    def spam(foo):
        return foo


    print(spam(13))         # ==> 13
    print(spam())           # ==> KeyError: 'foo'

    box.put("foo", 42)

    print(spam())           # ==> 42

The value to inject is not necessarily an object. You can pass a factory
function which will be used to produce a dependency. A factory function has
no arguments, and is assumed to have all the context it needs to work.

.. code:: python

    import picobox
    import random

    box = picobox.Box()
    box.put("foo", factory=lambda: random.choice(["spam", "eggs"]))


    @box.pass_("foo")
    def get_foo(foo):
        return foo


    print(get_foo())        # ==> spam
    print(get_foo())        # ==> eggs
    print(get_foo())        # ==> eggs
    print(get_foo())        # ==> spam
    print(get_foo())        # ==> eggs

Whereas factories are enough to implement whatever creation policy you want,
there's no good in repeating yourself again and again. That's why Picobox
introduces `scope` concept. Scope is a way to say whether you want to share
dependencies in some execution context or not.

For instance, you may want to share it globally (singleton) or create only one
instance per thread (threadlocal).

.. code:: python

    import picobox
    import random
    import threading

    box = picobox.Box()
    box.put("foo", factory=random.random, scope=picobox.threadlocal)
    box.put("bar", factory=random.random, scope=picobox.singleton)


    @box.pass_("foo")
    def spam(foo):
        print(foo)


    @box.pass_("bar")
    def eggs(bar):
        print(bar)


    # prints
    # > 0.9464005851114538
    # > 0.8585111290081737
    for _ in range(2):
        threading.Thread(target=spam).start()

    # prints
    # > 0.5333214411659912
    # > 0.5333214411659912
    for _ in range(2):
        threading.Thread(target=eggs).start()

But the cherry on the cake is a so called Picobox's stack interface. ``Box``
is great to manage dependencies but it requires to be created before using.
In practice it usually means you need to create it globally to get access
from various places. The stack interface is called to solve this by providing
general methods that will be applied to latest active box instance.

.. code:: python

    import picobox


    @picobox.pass_("foo")
    def spam(foo):
        return foo


    box_a = picobox.Box()
    box_a.put("foo", 13)

    box_b = picobox.Box()
    box_b.put("foo", 42)

    with picobox.push(box_a):
        print(spam())               # ==> 13

        with picobox.push(box_b):
            print(spam())           # ==> 42

        print(spam())               # ==> 13

    spam()                          # ==> RuntimeError: no boxes on the stack

When only partial overriding is necessary, you can chain pushed box so any
missed lookups will be proxied to the box one level down the stack.

.. code:: python

    import picobox


    @picobox.pass_("foo")
    @picobox.pass_("bar")
    def spam(foo, bar):
        return foo + bar


    box_a = picobox.Box()
    box_a.put("foo", 13)
    box_a.put("bar", 42)

    box_b = picobox.Box()
    box_b.put("bar", 0)

    with picobox.push(box_a):
        with picobox.push(box_b, chain=True):
            print(spam())           # ==> 13

The stack interface is recommended way to use Picobox because it allows to
switch between DI containers (boxes) on the fly. This is also the only way to
test your application because patching (mocking) globally defined boxes is
not a solution.

.. code:: python

    def test_spam():
        with picobox.push(picobox.Box(), chain=True) as box:
            box.put("foo", 42)
            assert spam() == 42

``picobox.push()`` can also be used as a regular function, not only as a
context manager.

.. code:: python

    def test_spam():
        box = picobox.push(picobox.Box(), chain=True)
        box.put("foo", 42)
        assert spam() == 42
        picobox.pop()

Every call to ``picobox.push()`` should eventually be followed by a corresponding
call to ``picobox.pop()`` to remove the box from the top of the stack, when you
are done with it.

.. note::

    Dependency Injection is usually used in applications, not libraries, to
    wire things together. Occasionally such need may come in libraries too, so
    picobox provides a :class:`picobox.Stack` class to create an independent
    non overlapping stack with boxes suitable to be used in such cases.

    Just create a global instance of stack (globals themeselves aren't bad),
    and use it as you'd use picobox stacked interface:

    .. code:: python

        import picobox

        stack = picobox.Stack()


        @stack.pass_("a", as_="b")
        def mysum(a, b):
            return a + b


        with stack.push(picobox.Box()) as box:
            box.put("a", 42)
            assert mysum(13) == 55


API reference
-------------

.. module:: picobox

Box
```

.. autoclass:: Box
    :members:

ChainBox
````````

.. autoclass:: ChainBox
    :members:

Scopes
``````

.. autoclass:: Scope
    :members: set, get

.. autodata:: singleton
    :annotation:

.. autodata:: threadlocal
    :annotation:

.. autodata:: contextvars
    :annotation:

.. autodata:: noscope
    :annotation:

.. autodata:: picobox.contrib.flaskscopes.application
    :annotation:

.. autodata:: picobox.contrib.flaskscopes.request
    :annotation:

Stacked API
```````````

.. autoclass:: Stack
    :members:

.. autofunction:: push
.. autofunction:: pop
.. autofunction:: put
.. autofunction:: get
.. autofunction:: pass_


Release Notes
-------------

.. note::

    Picobox follows `Semantic Versioning <https://semver.org>`_ which means
    backward incompatible changes will be released along with bumping major
    version component.

3.0.0
`````

Released on Apr 02, 2023.

* Add ``Python 3.10`` & ``Python 3.11`` support.

* Drop ``Python 2.7`` support. It's dead for more than a year anyway. Those who
  want to use picobox with ``Python 2`` should stick with ``2.x`` branch.

* Drop ``Python 3.4``, ``Python 3.5`` and ``Python 3.6`` support. They reached
  their end-of-life and are not maintained anymore.

* Add type annotations to public interface. Now users can use ``mypy`` to
  leverage type checking in their code base.

* Make some parameters keyword-only: ``factory`` and ``scope`` in ``Box.put()``,
  ``as_`` in ``Box.pass_()`` and ``chain`` in ``picobox.push()``.

* Use `PEP 621 <https://peps.python.org/pep-0621/>`_ ``pyproject.toml`` in
  a so-called source distribution.

2.2.0
`````

Released on Dec 24, 2018.

* Fix ``picobox.singleton``, ``picobox.threadlocal`` & ``picobox.contextvars``
  scopes so they do not fail with unexpected exception when non-string
  formattable missing key is passed.

* Add ``picobox.contrib.flaskscopes`` module with *application* and *request*
  scopes for Flask web framework.

* Add ``picobox.Stack`` class to create stacks with boxes on demand. Might
  be useful for third-party developers who want to use picobox yet avoid
  collisions with main application developers.

2.1.0
`````

Released on Sep 25, 2018.

* Add ``picobox.contextvars`` scope (python 3.7 and above) that can be used
  in asyncio applications to have a separate set of dependencies in all
  coroutines of the same task.

* Fix ``picobox.threadlocal`` issue when it was impossible to use any hashable
  key other than ``str``.

* Nested ``picobox.pass_`` calls are now squashed into one in order to
  improve runtime performance.

* Add ``Python 2.7`` support.

2.0.0
`````

Released on Mar 18, 2018.

* ``picobox.push()`` can now be used as a regular function as well, not only
  as a context manager. This is a breaking change because from now one a box
  is pushed on stack immediately when calling ``picobox.push()``, no need to
  wait for ``__enter__()`` to be called.

* New ``picobox.pop()`` function, that pops the box from the top of the stack.

* Fixed a potential race condition on concurrent calls to ``picobox.push()``
  that may occur in non-CPython implementations.

1.1.0
`````

Released on Dec 19, 2017.

* New ``ChainBox`` class that can be used similar to ``ChainMap`` but for
  boxes. This basically means from now on you can group few boxes into one
  view, and use that view to look up dependencies.

* New ``picobox.push()`` argument called ``chain`` that can be used to look
  up keys down the stack on misses.

1.0.0
`````

Released on Nov 25, 2017.

* First public release with initial bunch of features.
