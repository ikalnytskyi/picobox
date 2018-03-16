import picobox


box = picobox.Box()
box.put('magic', 12)

# The app instance exposed via this module is used to run the app for
# development (flask run) as well as for production (uWSGI, Gunicorn).
# Therefore, we need to push a box without popping so it will be used
# no matter which way we want to run the app.
#
# Examples:
#
#   $ FLASK_APP=wsgi.py flask run
#   $ gunicorn wsgi:app
#
# Alternatively, one can push and pop the box before and after the
# request (see Flask request context), but this way it would be harder
# to test the app since any attempt to override dependencies in tests
# will fail due to later attempt to push a new box by request hooks.
picobox.push(box)
from example import app  # noqa
