Flango
======
Flango is a WSGI based webframework in pure Python, without any third-party dependency.
flango include a simple router, which provide the request routing, a template engine
for template rendering, a simple wrapper for WSGI request and response, and
a ORM framework for sqlite3.

- [ORM for Sqlite3](https://github.com/hziling/ORM)
- [Template Engine](https://github.com/hziling/template)
- [Router](https://github.com/hziling/router)

Example
-------
+ HelloWorld

    from flango import flango

    app = flango.Flango('/')

    @app.route('/hello/<name>')
    def hello(name):
        return 'Hello {0}!'.format(name)

    app.run(DEBUG=True)
+ [A Blog based Flango](https://github.com/hziling/flango/tree/master/examples/blog)

![image](https://github.com/hziling/flango/blob/master/examples/blog/example_images/1.jpg)

![image](https://github.com/hziling/flango/blob/master/examples/blog/example_images/2.jpg)
Tests
-----
    ..............................................................................................
    ----------------------------------------------------------------------
    Ran 94 tests in 0.493s

    OK
