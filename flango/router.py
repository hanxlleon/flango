# -*- coding: utf-8 -*-
import re


class RouterException(Exception):
    pass


class Router(object):
    """A Router for url like Flask.

    Firstly, register a url with a function and methods.

    The url can be a pattern like:
    "/author/<username>" which will match urls "http://hostname:port/author/Jone" or "http://hostname:port/author/Bob",
    "/post/<int:id>" which will match urls "http://hostname:port/post/1" or "http://hostname:port/post/20".

    Then we can get the function with the registered path or get the path with whe registered function.
    """

    def __init__(self):
        # key: path pattern, value: function and args
        self.rules = {}
        self.url_pattern = re.compile(
            r'(?P<prefix>(/\w*)+)(<((?P<type>\w+):)?(?P<args>\w+)>)?'
        )
        self.methods = {}
        self.methods.setdefault('GET', [])
        self.methods.setdefault('POST', [])
        self.methods.setdefault('PUT', [])
        self.methods.setdefault('DELETE', [])

    def register(self, path, fn, methods):
        if not callable(fn):
            raise RouterException('Router only accept callable object.')

        for method in methods:
            self.methods[method].append(fn)

        g = self.url_pattern.match(path)
        if not g:
            raise RouterException('Router rules: "{0}" can not be accept.'.format(path))

        p = g.group('prefix')
        if g.group('type'):
            assert g.group('type') == 'int'
            p = r'{0}(?P<args>\d+)$'.format(p)
        elif g.group('args'):
            p = r'{0}(?P<args>\w+)$'.format(p)
        else:
            p = r'{0}$'.format(p)

        self.rules[re.compile(p)] = (fn, g.group('args')) if g.group('args') else (fn, None)

    def __call__(self, path, method='GET'):
        return self.get(path, method)

    def get(self, path, method='GET'):
        for rule, value in self.rules.iteritems():
            g = rule.match(path)
            if g:
                fn, args = value
                method = method.upper()
                if self.methods.get(method) is None:
                    raise RouterException('Request method: "{0}" is not allowed in this app.'.format(method))
                if args:
                    return fn, {args: g.group('args')}
                else:
                    return fn, None
        else:
            raise RouterException('Router rules: "{0}" can not be accept.'.format(path))

    def url_for(self, fn, **kwargs):
        for rule, value in self.rules.iteritems():
            func, args = value
            if fn != func:
                continue
            if args:
                if args not in kwargs.keys():
                    raise RouterException('Need an argument.')

                return rule.pattern.replace('(?P<args>\d+)$', str(kwargs[args])).replace('(?P<args>\w+)$', str(kwargs[args]))
            return rule.pattern.rstrip('$')
        else:
            raise RouterException("Callable object doesn't match any routing rule.")

    def all_callables(self):
        """ All registered functions. """
        return [fn for fn, args in self.rules.values()]



