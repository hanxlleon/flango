# coding: utf-8

import re
import os
import collections


_CACHE_CAPACITY = 128


class Scanner(object):

    def __init__(self, source):
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
        return t

    @property
    def empty(self):
        return self.remain == ''


class BaseNode(object):

    def __init__(self, text, indent, block):
        self.text = text
        self.indent = indent
        self.block = block

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

    def __init__(self, source, path=''):
        if not source:
            raise ValueError('invalid parameter')

        self.scanner = Scanner(source)
        self.path = path
        self.nodes = []
        self.parents = None

        self._parse()
        self.intermediate = self._compile()

    def _parse(self):
        indent = 0
        in_block = []

        def in_block_top():
            return in_block[-1] if in_block else None

        while not self.scanner.empty:
            token = self.scanner.next_token()

            if not token:
                self.nodes.append(TextNode(self.scanner.remain, indent, in_block_top()))
                break

            if self.scanner.pretext:
                self.nodes.append(TextNode(self.scanner.pretext, indent, in_block_top()))

            variable, endblock, end, statement, keyword, suffix = token.groups()

            if variable:
                self.nodes.append(VariableNode(str(variable), indent, in_block_top()))
            elif endblock:
                if end == 'block':
                    in_block.pop()
                indent -= 1
            elif statement:
                if keyword == 'include':
                    filename = re.sub('\'|\"', '', suffix)
                    nodes = Loader(self.path).load(filename).nodes
                    for node in nodes:
                        node.indent += indent
                    self.nodes.extend(nodes)
                    continue
                elif keyword == 'extends':
                    if self.nodes:
                        raise TemplateException('Template syntax error: extends tag must be '
                                                'at the beginning of the file.')
                    filename = re.sub('\'|\"', '', suffix)
                    self.parents = Loader(self.path).load(filename)
                    continue
                elif keyword == 'block':
                    in_block.append(suffix)
                    if not self.parents:
                        text = 'block%{0}'.format(suffix)
                        self.nodes.append(KeyNode(text, indent, in_block_top()))
                    continue
                if keyword in ['else', 'elif', 'except', 'finally']:
                    key_indent = indent - 1
                else:
                    key_indent = indent
                    indent += 1
                syntax = '{0}:'.format(statement)
                self.nodes.append(
                    KeyNode(syntax, key_indent, in_block_top()))
            else:
                raise TemplateException('Template syntax error.')

    def _compile(self):
        block = {}

        if self.parents:
            parents_gen = ''.join(node.generate() for node in self.parents.nodes)
            pattern = re.compile(r'block%(?P<block_name>\w+)')
            for node in self.nodes:
                if node.block:
                    block.setdefault(node.block, []).append(node.generate())
            for token in pattern.finditer(parents_gen):
                block_name = token.group('block_name')
                if block_name in block.keys():
                    parents_gen.replace(token.group(), ''.join(block[block_name]))
                else:
                    parents_gen.replace(token.group(), '')
        else:
            parents_gen = ''.join(node.generate() for node in self.nodes)

        return compile(parents_gen, '<string>', 'exec')

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


class Loader(object):
    def __init__(self, path='', engine=Template, cache_capacity=_CACHE_CAPACITY):
        self.path = path
        self.engine = engine
        self.cache = LRUCache(capacity=cache_capacity)

    def load(self, filename):
        if not self.path.endswith(os.sep) and self.path != '':
            self.path = self.path + os.sep

        p = ''.join([self.path, filename])

        cache_instance = self.cache.get(p)
        if cache_instance != -1:
            return cache_instance

        if not os.path.isfile(p):
            raise TemplateException('Template file {0} is not exist.'.format(p))

        with open(p) as f:
            self.cache.set(p, self.engine(f.read()))

        return self.cache.get(p)


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

    # t2 = """
    #     <table>
    #     <tr>{% for v in table[0].values() %}
    #         {% if v % 2 %}
    #         <td>{{ col }}<td/>
    #         {% else %}
    #         <td>{{ col + str(v) }}<td/>
    #         {%endif%}
    #         {% endfor %}
    #     </tr>
    #     </table>"""
    #
    # s = Template(t2)
    # r = s.render(col='hello', table=table)
    # print r

    lunar_tmpl = Template("""
    <table>
    {% for i in range(3) %}
    {{ i }}
    {% endfor %}
    </table>""").render()

    print lunar_tmpl


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