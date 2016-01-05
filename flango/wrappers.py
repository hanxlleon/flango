import threading
import httplib
from cgi import FieldStorage
from urlparse import parse_qs
from Cookie import SimpleCookie
from collections import MutableMapping


class HttpHeaders(MutableMapping):
    """ Wrapper for Http-like headers.

    Dict-like key-value store, but keys are Http-Header-Case foramt.
    value is a list, but the magic method __getitem__ will only return the
    latest value added.
    """
    def __init__(self, **kwargs):
        self._dict = {self.normalize_key(k): [v] for k, v in kwargs.iteritems()}

    def __setitem__(self, key, value):
        self._dict.setdefault(self.normalize_key(key), []).append(value)

    def __getitem__(self, key):
        return self._dict[self.normalize_key(key)][-1]

    def __contains__(self, key):
        return self.normalize_key(key) in self._dict.keys()

    def __delitem__(self, key):
        del self._dict[self.normalize_key(key)]

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)

    def append(self, key, value):
        self._dict.setdefault(self.normalize_key(key), []).append(value)

    def get_list(self, key):
        return self._dict.get(self.normalize_key(key), [])

    def as_list(self):
        return [(k, self.get(k)) for k in self._dict.keys()]

    @staticmethod
    def normalize_key(key):
        """ Converts a key to Http-Header-Case"""
        return '-'.join(w.capitalize() for w in key.split('-'))


class BaseObject(threading.local):
    """Base class for request and response.
    Provide a thread safe space.
    """
    pass


class Request(BaseObject):
    def __init__(self, environ=None):
        super(Request, self).__init__()
        self.environ = environ if environ else {}
        self._args = {}
        self._forms = {}

    def bind(self, environ):
        self.environ = environ

    @property
    def forms(self):
        if self._forms:
            return self._forms

        forms = FieldStorage(fp=self.environ['wsgi.input'], environ=self.environ)
        for k in forms.keys():
            if isinstance(forms[k], list):
                self._forms[k] = [v.value for v in forms[k]]
            elif forms[k].filename:
                self._forms[k] = forms[k]
            else:
                self._forms[k] = forms[k].value

        return self._forms

    @property
    def args(self):
        if self._args:
            return self._args

        args = parse_qs(self.query)
        for k, v in args.iteritems():
            if len(v) == 1:
                self._args[k] = v[0]
            else:
                self._args[k] = v

        return self._args

    @property
    def path(self):
        return self.environ.get('PATH_INFO', '/')

    @property
    def headers(self):
        return self.environ

    @property
    def method(self):
        return self.environ.get('REQUEST_METHOD', 'GET')

    @property
    def query(self):
        return self.environ.get('QUERY_STRING', '')

    @property
    def cookies(self):
        return SimpleCookie(self.environ.get('HTTP_COOKIE', ''))

    @property
    def if_modified_since(self):
        return self.environ.get('HTTP_IF_MODIFIED_SINCE', '')


class Response(BaseObject):

    def __init__(self, body, code=200, content_type='text/html'):
        super(Response, self).__init__()
        self.headers = HttpHeaders()
        self._cookies = None
        self._status = code
        self.content_type = content_type

        # body
        self._body = None
        self.set_body(body)

    @property
    def cookies(self):
        if not self._cookies:
            self._cookies = SimpleCookie()
        return self._cookies

    def set_cookie(self, key, value, **kwargs):
        self.cookies[key] = value
        for k, v in kwargs.iteritems():
            self.cookies[key][k] = v

    @property
    def status(self):
        return ' '.join([str(self._status), httplib.responses.get(self._status)])

    def set_status(self, s):
        self._status = s

    @property
    def headerlist(self):
        return self.headers.as_list()

    @property
    def body(self):
        return self._body

    def set_body(self, body):
        self._body = str(body)

    def get_content_type(self):
        return self.headers['Content-Type']

    def set_content_type(self, value):
        self.headers['Content-Type'] = value

    content_type = property(
        get_content_type, set_content_type, None, get_content_type.__doc__)