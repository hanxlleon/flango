"""
Bottle-like Servers strategy.

Method flango.run accept a subclass of ServerAdapter, create a server
instance and run applications using the run interface provided by ServerAdapter.

So the server must implement the interface 'run' provided by ServerAdapter.
"""


class ServerAdapter(object):
    def __init__(self, host='127.0.0.1', port=8000):
        self.host = host
        self.port = port

    def __repr__(self):
        return '{0} ({1}:{2})'.format(self.__class__.__name__, self.host, self.port)

    def run(self, app):
        raise NotImplementedError


class WSGIRefServer(ServerAdapter):

    def run(self, app):
        from wsgiref.simple_server import make_server
        httpd = make_server(self.host, self.port, app)
        httpd.serve_forever()
