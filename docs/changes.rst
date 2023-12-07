Changes
=======

.. note::

    Picobox follows `Semantic Versioning <https://semver.org>`_ which means
    backward incompatible changes will be released along with bumping major
    version component.

4.1.0
-----

(unreleased)

* Add ``picobox.ext.wsgiscopes`` extensions with ``application`` and ``request``
  scopes for WSGI applications.

* Add ``picobox.ext.asgiscopes`` extensions with ``application`` and ``request``
  scopes for ASGI applications.

* Fix a bug when a coroutine function wrapped with ``@picobox.pass_()``
  lost its coroutine function marker, i.e. ``inspect.iscoroutinefunction()``
  returned ``False``.

* Fix a bug when ``picobox.pop()`` threw a generic ``IndexError`` when there
  were no pushed boxes on stack. Now ``RuntimeError`` exception is thrown
  instead with a good-looking error message. The behavior is now consistent
  with other functions such as ``picobox.put()`` or ``picobox.get()``.

4.0.0
-----

Released on Nov 20, 2023.

* **BREAKING**: The ``picobox.contrib`` package is renamed into ``picobox.ext``.

* Add ``Python 3.12`` support.

* Drop ``Python 3.7`` support. It reached its end-of-life recently.

* Fix ``@picobox.pass_()`` decorator issue when it was shadowing a return type
  of the wrapped function breaking code completion in some LSP servers.

* Fix ``picobox.push()`` context manager issue when it wasn't announcing
  properly its return type breaking code completion in some LSP servers for the
  returned object.

* Fix ``Box.put()`` and ``picobox.put()`` to require either ``value``
  or ``factory`` argument. Previously, they could have been invoked with ``key``
  argument only, which makes no sense and causes runtime issues later on.

3.0.0
-----

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
-----

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
-----

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
-----

Released on Mar 18, 2018.

* ``picobox.push()`` can now be used as a regular function as well, not only
  as a context manager. This is a breaking change because from now one a box
  is pushed on stack immediately when calling ``picobox.push()``, no need to
  wait for ``__enter__()`` to be called.

* New ``picobox.pop()`` function, that pops the box from the top of the stack.

* Fixed a potential race condition on concurrent calls to ``picobox.push()``
  that may occur in non-CPython implementations.

1.1.0
-----

Released on Dec 19, 2017.

* New ``ChainBox`` class that can be used similar to ``ChainMap`` but for
  boxes. This basically means from now on you can group few boxes into one
  view, and use that view to look up dependencies.

* New ``picobox.push()`` argument called ``chain`` that can be used to look
  up keys down the stack on misses.

1.0.0
-----

Released on Nov 25, 2017.

* First public release with initial bunch of features.
