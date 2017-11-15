Picobox
=======

.. image:: https://img.shields.io/pypi/v/picobox.svg
   :target: https://pypi.python.org/pypi/picobox

.. image:: https://travis-ci.org/ikalnytskyi/picobox.svg
   :target: https://travis-ci.org/ikalnytskyi/picobox

.. image:: https://codecov.io/gh/ikalnytskyi/picobox/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/ikalnytskyi/picobox

.. image:: https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg
   :target: https://saythanks.io/to/ikalnytskyi

Picobox is opinionated dependency injection framework designed to be clean,
pragmatic and with Python in mind. No complex graphs, no implicit injections,
no type bindings – just picoboxes, and explicit demands!


Why?
----

Because we usually want to decouple our code and Python lack of clean and
pragmatic solutions (even third parties).


Features
--------

* Support both values and factories.
* Support scopes (e.g. singleton, threadlocal).
* Push boxes on stack, and use the top one to access values.
* Thread-safe.
* Lightweight ( ~141 LOC ).
* Zero dependencies.
* Pure Python.



Quickstart
----------

First

.. code:: bash

    $ [sudo] python -m pip install picobox

and then

.. code:: python

    import picobox
    import requests

    @picobox.pass_('conf')
    @picobox.pass_('requests', as_='session')
    def get_resource(uri, session, conf):
        return session.get(conf['base_uri'] + uri)

    box = picobox.Box()
    box.put('conf', {'base_uri': 'http://example.com'})
    box.put('requests', factory=requests.Session, scope=picobox.threadlocal)

    with picobox.push(box):
        get_resource('/resource', requests.Session(), {})
        get_resource('/resource', requests.Session())
        get_resource('/resource')


Links
-----

* Documentation: https://picobox.readthedocs.io
* Source: https://github.com/ikalnytskyi/picobox
* Bugs: https://github.com/ikalnytskyi/picobox/issues
