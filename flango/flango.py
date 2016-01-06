#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Flango: A simple WSGI based webframework for learning.

Flango is a WSGI based webframework in pure Python, without any third-party dependency.
flango include a simple router, which provide the request routing, a template engine
for template rendering, a simple wrapper for WSGI request and response, and
a ORM framework for sqlite3.
"""

import json
import os
import time
import sys
import traceback
import threading
import mimetypes
from urllib import quote

from .server import ServerAdapter, WSGIRefServer
from .template import Loader
from .wrappers import Request, Response
from .router import Router, RouterException


class _Stack(threading.local):
    def __init__(self):
        super(_Stack, self).__init__()
        self._stack = []

    def push(self, app):
        self._stack.append(app)

    def pop(self):
        try:
            self._stack.pop()
        except IndexError:
            return None

    def top(self):
        try:
            return self._stack[-1]
        except IndexError:
            return None

    def __len__(self):
        return len(self._stack)

    def empty(self):
        return len(self._stack) == 0

    def __repr__(self):
        return 'app_stack with {0} applications'.format(len(self))


class FlangoException(Exception):
    def __init__(self, code, response, server_handler, DEBUG=False):
        self._DEBUG = DEBUG
        self._response = response
        self._response.set_status(code)
        self._server_handler = server_handler

    def __call__(self):
        if self._DEBUG:
            body = '<br>'.join([self._response.status, traceback.format_exc().replace('\n', '<br>')])
        else:
            body = self._response.status

        self._response.set_body(body)
        self._server_handler(self._response.status, self._response.headerlist)
        return [self._response.body]


class Flango(object):
    """Main object of this funny web frameWork."""

    def __init__(self, pkg_name, template='template', static='static'):
        # router
        self._router = Router()

        # request and response
        self._request = Request()
        self._response = Response(None)

        # template
        self.package_name = pkg_name
        # where is the app root located?
        self.root_path = self._get_package_path(self.package_name).replace('\\', '\\\\')  # '\u' escape

        self.loader = Loader(os.sep.join([self.root_path, template]))

        # static file
        self.static_folder = static
        self.abspath = None
        self.modified = None
        self.static_url_cache = {}

        # session
        self._session = self._request.cookies

        # server handler
        self._server_handler = None

        # debug
        self.DEBUG = False

        # config
        self.config = {}
        self.config.setdefault('DATABASE_NAME', 'flango.db')

        # push to the _app_stack
        global app_stack
        app_stack.push(self)

    def _get_package_path(self, name):
        """Returns the path to a package or cwd if that cannot be found."""
        try:
            return os.path.abspath(os.path.dirname(sys.modules[name].__file__))
        except (KeyError, AttributeError):
            return os.getcwd()

    def route(self, path, methods=['GET']):
        if path is None:
            raise RouterException()
        methods = [m.upper() for m in methods]

        def wrapper(fn):
            self._router.register(path, fn, methods)
            return fn

        return wrapper

    @property
    def session(self):
        return self._session

    def run(self, server=WSGIRefServer, host='localhost', port=8000, DEBUG=False):
        self.DEBUG = DEBUG
        if isinstance(server, type) and issubclass(server, ServerAdapter):
            server = server(host=host, port=port)
        else:
            raise RuntimeError('Server must be a subclass of ServerAdapter.')

        print('running on {0}:{1}'.format(host, port))
        try:
            server.run(self)
        except KeyboardInterrupt:
            pass

    def jsonify(self, *args, **kwargs):
        response = Response(body=json.dumps(dict(*args, **kwargs)), code=200)
        response.set_content_type('application/json')
        return response

    def render(self, filename, **context):
        app_namespace = sys.modules[self.package_name].__dict__
        context.update(globals())
        context.update(app_namespace)
        return self.loader.load(filename).render(**context)

    def not_found(self):
        return Response(body='<h1>404 Not Found</h1>', code=404)

    def not_modified(self):
        response = Response('', code=304)
        # Don't need Content-Type here.
        del response.headers['Content-Type']
        return response

    def redirect(self, location, code=302):
        response = Response(body='<p>Redirecting...</p>', code=code)
        response.headers['Location'] = location
        return response

    def url_for(self, fn, filename=None, **kwargs):
        # URLs for static files are constructed according to
        # current wsgi environ(HTTP_HOST, SERVER_NAME, etc.)
        if fn == self.static_folder and filename:
            if filename in self.static_url_cache.keys():
                return self.static_url_cache[filename]
            else:
                url = self.construct_url(filename)
                # Cache the URL
                self.static_url_cache[filename] = url
                return url
        # Router function URLs are given by the router.
        if kwargs:
            return self._router.url_for(fn, **kwargs)
        return self._router.url_for(fn)

    def construct_url(self, filename):
        environ = self._request.headers
        url = environ['wsgi.url_scheme'] + '://'
        if environ.get('HTTP_HOST'):
            url += environ['HTTP_HOST']
        else:
            url += environ['SERVER_NAME']

            if environ['wsgi.url_scheme'] == 'https':
                if environ['SERVER_PORT'] != '443':
                    url += ':' + environ['SERVER_PORT']
            else:
                if environ['SERVER_PORT'] != '80':
                    url += ':' + environ['SERVER_PORT']

        url += quote(environ.get('SCRIPT_NAME', ''))
        if environ.get('QUERY_STRING'):
            url += '?' + environ['QUERY_STRING']

        url += '/' + '/'.join([self.static_folder, filename])
        return url

    @property
    def request(self):
        return self._request

    @property
    def response(self):
        return self._response

    def get_content_type(self):
        fallback_content_type = 'text/plain'
        mime_type = mimetypes.guess_type(self.abspath)[0]
        if mime_type:
            return mime_type
        else:
            return fallback_content_type

    def get_modified_time(self):
        stats = os.stat(self.abspath)

        last_modified_time = time.gmtime(stats.st_mtime)
        return last_modified_time

    def should_return_304(self):
        if_modified_since_str = self._request.if_modified_since
        if if_modified_since_str:
            if_modified_since_time = time.strptime(if_modified_since_str, '%a, %d %b %Y %H:%M:%S %Z')
            if if_modified_since_time >= self.modified:
                return True
        return False

    def is_static_file_request(self):
        return self._request.path.lstrip('/').startswith(self.static_folder)

    def handle_static(self, path):
        response = Response(None)

        # This is the absolute path of a static file on the filesystem
        self.abspath = self.root_path + path

        if not os.path.exists(self.abspath) or not os.path.isfile(self.abspath):
            return self.not_found()

        content_type = self.get_content_type()
        response.set_content_type(content_type)

        self.modified = self.get_modified_time()

        if self.should_return_304():
            return self.not_modified()

        if 'Last-Modified' not in response.headers.keys():
            last_modified_str = time.strftime(
                '%a, %d %b %Y %H:%M:%S UTC', self.modified)
            response.headers['Last-Modified'] = last_modified_str

        with open(self.abspath, 'r') as f:
            response.set_body(body=(f.read()))
        return response

    def handle_router(self):
        try:
            handler, args = self._router.get(self._request.path, self._request.method)
        except RouterException:
            # No handler is found, assume it's a 404.
            return self.not_found()

        return handler(**args) if args else handler()

    def __call__(self, environ, start_response):
        self._response = Response(None)
        self._request = Request(None)
        self._server_handler = start_response
        self._request.bind(environ)

        if self.is_static_file_request():
            r = self.handle_static(self._request.path)
        else:
            try:
                r = self.handle_router()
            except Exception:
                return FlangoException(500, self._response, self._server_handler, self.DEBUG)()

        # Static files, 302, 304 and 404
        if isinstance(r, Response):
            self._response = r
            self._server_handler(r.status, r.headerlist)
            return [r.body]

        # Normal html
        self._response.set_body(body=r)
        self._response.set_status(200)
        start_response(self._response.status, self._response.headerlist)
        return [self._response.body]


"""
default methods and properties
"""

# global app stack.
app_stack = _Stack()

# default app
default_app = app_stack.top()

if not default_app:  # hack for shell
    default_app = Flango('/')

# shell
request = app_stack.top().request
response = app_stack.top().response
session = app_stack.top().session