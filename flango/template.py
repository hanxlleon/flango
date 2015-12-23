# coding: utf-8

import re
import collections


class Scanner(object):

    def __init__(self, source):
        self.offset = 0
        self.re_token = re.compile(r'''
            {{\s*(?P<var>.+?)\s*}}  # variable: {{ name }}
            |  # or
            {%\s*(?P<endblock>end(if|for|while|block))\s*%}  # endblock: {% endblock %}
            |  # or
            {%\s*(?P<statement>(?P<keyword>\w+)\s*(.+?))\s*%}  # statement: {% for i in range(10) %}
            ''', re.VERBOSE)
        self.pretext = ''
        self.remain = source

    def next_token(self):
        t = self.re_token.search(self.remain)
        if not t:
            return None

        self.pretext = self.remain[:t.start()]
        self.remain = self.remain[t.end():]
        self.offset = t.end()
        return t

    @property
    def empty(self):
        return self.remain == ''


class BaseNode(object):

    def __init__(self, text, indent):
        self.text = text
        self.indent = indent

    def generate(self):
        raise NotImplementedError()


class TextNode(BaseNode):
    def generate(self):
        return '{0}_stdout.append(\'\'\'{1}\'\'\')\n'.format(' '*self.indent, self.text)


class VariableNode(BaseNode):
    def generate(self):
        return '{0}_stdout.append({1})\n'.format(' '*self.indent, self.text)


class KeyNode(BaseNode):
    def generate(self):
        return '{0}{1}\n'.format(' '*self.indent, self.text)


class TemplateException(Exception):
    pass


class Template(object):

    def __init__(self, source):
        self.scanner = Scanner(source)
        self.nodes = []
        self.intermediate = []

        if source:
            self._parse()
            self._compile()
        else:
            raise ValueError('invalid parameter')

    def _parse(self):
        indent = 0

        while not self.scanner.empty:
            token = self.scanner.next_token()
            if token:
                self.nodes.append(
                    TextNode(self.scanner.pretext, indent))
            else:
                self.nodes.append(
                    TextNode(self.scanner.remain, indent))
                break

            variable, endblock, end, statement, keyword, suffix = token.groups()

            if variable:
                self.nodes.append(
                    VariableNode(str(variable), indent))
            elif endblock:
                indent -= 1
            elif statement:
                if keyword in ['else', 'elif', 'except', 'finally']:
                    key_indent = indent - 1
                else:
                    key_indent = indent
                    indent += 1
                syntax = '{0}:'.format(statement)
                self.nodes.append(
                    KeyNode(syntax, key_indent))
            else:
                raise TemplateException('Template syntax error.')

    def _compile(self):
        c = ''.join(node.generate() for node in self.nodes)
        self.intermediate = compile(c, '<string>', 'exec')

    def render(self, **context):
        context['_stdout'] = []
        exec(self.intermediate, context)
        return ''.join(map(str, context['_stdout']))


class LRUCache(object):
    """ Simple LRU cache for template instance caching.

    in fact, the OrderedDict in collections module or
    @functools.lru_cache is working well too.
    """
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = collections.OrderedDict()

    def get(self, key):
        """ Return -1 if catched KeyError exception."""
        try:
            value = self.cache.pop(key)
            self.cache[key] = value
            return value
        except KeyError:
            return -1

    def set(self, key, value):
        try:
            self.cache.pop(key)
        except KeyError:
            if len(self.cache) >= self.capacity:
                self.cache.popitem(last=False)

        self.cache[key] = value


if __name__ == '__main__':
    table = [dict(a=1, b=2, c=3, d=4, e=5, f=6, g=7, h=8, i=9, j=10)]

    # t = """
    #     <table>
    #     {% for row in table %}
    #     <tr>{% for col in row.values() %}
    #         <td>{{ col }}<td/>
    #         {% endfor %}
    #     </tr>{% endfor %}
    #     </table>"""
    #
    # s = Template(t)
    # r = s.render(col='hello', table=table)

    t2 = """
        <table>
        <tr>{% for v in table[0].values() %}
            {% if v % 2 %}
            <td>{{ col }}<td/>
            {% else %}
            <td>{{ col + str(v) }}<td/>
            {%endif%}
            {% endfor %}
        </tr>
        </table>"""

    s = Template(t2)
    r = s.render(col='hello', table=table)
    print r


    # from django.conf import settings
    # settings.configure()
    # from django.template import Context as DjangoContext
    # from django.template import Template as DjangoTemplate
    # django_tmpl = DjangoTemplate(
    #     """
    #     <table>
    #     {% for row in table %}
    #     <tr>
    #         <td>{{ col }}<td/>
    #     </tr>{% endfor %}
    #     </table>"""
    # )
    #
    # context = DjangoContext({'col': 'hello', 'table': table})
    # print django_tmpl.render(context)


