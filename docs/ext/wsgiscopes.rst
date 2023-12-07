WSGI scopes
===========

The Web Server Gateway Interface (WSGI) is a standard interface between web
server software and web applications written in Python. It's synchronous and
has been designed long ago before asynchronous Python came to be. The
long-standing web frameworks of the Python landscape, including Django, Flask,
Falcon, Pyramid, and Bottle are all WSGI-based frameworks. WSGI is a Python
standard described in detail in :pep:`3333`.

When it comes to *web applications*, there are two notable lifetimes one may
want to tie their objects to: *application* and *request*. For instance, it's
typical to tie a database connection (or session) to the lifetime of a web
request, i.e. retrieving a database connection from a connection pool on demand
and returning it to the pool when the request ends.

.. code:: python

    import bottle
    import picobox
    import picobox.ext.wsgiscopes as wsgiscopes
    import sqlalchemy as sa

    app = bottle.Bottle()
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    Users = sa.Table("users", metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(42)),
    )

    @app.route("/leia")
    def get_leia():
        user = get_user_by_name("Leia")
        return {"id": user[0], "name": user[1]}

    # The injected connection instance is shared across the same web request,
    # no matter how many times it's injected and where.
    @picobox.pass_("connection")
    def get_user_by_name(name, *, connection):
        statement = sa.select(Users).where(Users.c.name == name).limit(1)
        for row in connection.execute(statement):
            return row

    with picobox.push(picobox.Box()) as box:
        # Create a database table and populate it with some data for the
        # purpose of this example.
        with engine.begin() as connection:
            metadata.create_all(bind=connection)
            connection.execute(sa.insert(Users).values([
                {"id": 1, "name": "Luke"},
                {"id": 2, "name": "Leia"},
            ]))

        # Use 'engine.connect()' to construct a database connection instance
        # and share that instance across the same web request.
        box.put("connection", factory=engine.connect, scope=wsgiscopes.request)

        # The WSGI application MUST be wrapped into 'ScopeMiddleware' before
        # using any scope from 'wsgiscopes'.
        bottle.run(wsgiscopes.ScopeMiddleware(app), debug=True)


API reference
-------------

.. module:: picobox.ext.wsgiscopes

.. autodata:: ScopeMiddleware
  :annotation:

.. autodata:: application
  :annotation:

.. autodata:: request
  :annotation:
