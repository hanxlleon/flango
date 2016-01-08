# -*- coding: utf-8 -*-

"""
    A simple router like Flask.

    Firstly, register a URL with a function and methods.

                        >>>def hello(name):
                        ...    return 'Hello {0}!'.format(name)

                        >>>router = Router()
                        >>>router.register('/hello/<name>', hello, ['GET'])

    The URL also can be a pattern like:
    "/author/<username>" which will match URLs "http://hostname:port/author/Jone" or "http://hostname:port/author/Bob",
    "/post/<int:id>" which will match URLs "http://hostname:port/post/1" or "http://hostname:port/post/20".

    Then we can get the function with the registered path:

                        >>>print router.get('/hello/world')
                        Out: (<function hello at 0x0000000007BE9128>, {'name': 'world'})

    or get the path with the registered function:

                        >>>print router.url_for(hello, name='world')
                        Out: /hello/world
"""

import re


class RouterException(Exception):
    pass


class Router(object):

    def __init__(self):
        # key: path pattern, value: function and args
        self.rules = {}
        self.url_pattern = re.compile(
            r'(?P<prefix>(/\w*)+)(<((?P<type>\w+):)?(?P<args>\w+)>)?'
        )
        self.methods = {
            'GET': [],
            'POST': [],
            'PUT': [],
            'DELETE': []
        }

    def register(self, path, func, methods):
        if not callable(func):
            raise RouterException('Router only accept callable object.')

        for method in methods:
            self.methods[method].append(func)

        token = self.url_pattern.match(path)
        if not token:
            raise RouterException('Router rules: "{0}" can not be accept.'.format(path))

        path_pattern = token.group('prefix')
        if token.group('type'):
            assert token.group('type') == 'int'
            path_pattern = r'{0}(?P<args>\d+)$'.format(path_pattern)
        elif token.group('args'):
            path_pattern = r'{0}(?P<args>\w+)$'.format(path_pattern)
        else:
            path_pattern = r'{0}$'.format(path_pattern)

        self.rules[re.compile(path_pattern)] = (func, token.group('args')) if token.group('args') else (func, None)

    def __call__(self, path, method='GET'):
        return self.get(path, method)

    def get(self, path, method='GET'):
        for rule, value in self.rules.iteritems():
            token = rule.match(path)
            if token:
                func, args = value
                method = method.upper()
                if self.methods.get(method) is None:
                    raise RouterException('Request method: "{0}" is not allowed in this app.'.format(method))

                if args:
                    return func, {args: token.group('args')}
                else:
                    return func, None
        else:
            raise RouterException('Router rules: "{0}" can not be accept.'.format(path))

    def url_for(self, func, **kwargs):
        for rule, value in self.rules.iteritems():
            function, args = value
            if function != func:
                continue
            if args:
                if args not in kwargs.keys():
                    raise RouterException('Required an argument.')

                return rule.pattern.replace('(?P<args>\d+)$', str(kwargs[args])).replace('(?P<args>\w+)$', str(kwargs[args]))
            return rule.pattern.rstrip('$')
        else:
            raise RouterException("Callable object doesn't match any routing rule.")

    def all_callables(self):
        """ All registered functions. """
        return [func for func, _ in self.rules.values()]