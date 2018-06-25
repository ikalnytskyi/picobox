"""Py2/Py3 compatibility misc."""

import sys


if sys.version_info[0] > 2:
    signature = __import__('inspect').signature
else:
    # inspect.signature has been introduced in Python 3.3 and older versions
    # have to use third-party 'funcsigs' package instead.
    signature = __import__('funcsigs').signature


# This piece of code is copied from six library and is distributed under the
# same license (http://six.readthedocs.io/#six.add_metaclass).
def add_metaclass(metaclass):
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper
