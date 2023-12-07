API reference
=============

.. module:: picobox

Box
---

.. autoclass:: Box
    :members:

ChainBox
--------

.. autoclass:: ChainBox
    :members:

Scopes
------

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

Stacks
------

.. autoclass:: Stack
    :members:

.. autofunction:: push
.. autofunction:: pop
.. autofunction:: put
.. autofunction:: get
.. autofunction:: pass_
