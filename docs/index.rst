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


.. toctree::
    :maxdepth: 2

    quickstart
    ext/index
    api
    changes

    Source <https://github.com/ikalnytskyi/picobox>
    Bugs <https://github.com/ikalnytskyi/picobox/issues>
    PyPI <https://pypi.org/project/picobox/>
