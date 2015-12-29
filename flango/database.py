# coding: utf-8
import sqlite3
import sys
import threading
from datetime import datetime


class Field(object):
    def __init__(self, column_type):
        self.column_type = column_type
        self.name = None

    def create_sql(self):
        raise NotImplementedError


class IntegerField(Field):
    def __init__(self):
        super(IntegerField, self).__init__('INTEGER')

    def create_sql(self):
        return '"{0}" {1}'.format(self.name, self.column_type)

    def sql_format(self, data):
        return str(int(data))


class CharField(Field):
    def __init__(self, max_lenth=255):
        self.max_lenth = max_lenth
        super(CharField, self).__init__('VARCHAR')

    def create_sql(self):
        return '"{0}" {1}({2})'.format(self.name, self.column_type, self.max_lenth)

    def sql_format(self, data):
        return '"{0}"'.format(str(data))


class DateTimeField(Field):
    def __init__(self):
        super(DateTimeField, self).__init__('DATETIME')

    def create_sql(self):
        return '"%s" %s' % (self.name, "DATETIME")

    def sql_format(self, data):
        return '"{0}"'.format(data.strftime('%Y-%m-%d %H:%M:%S'))


class PrimaryKeyField(IntegerField):
    def __init__(self):
        super(PrimaryKeyField, self).__init__()

    def create_sql(self):
        return '"%s" %s NOT NULL PRIMARY KEY' % (self.name, "INTEGER")


class ForeignKeyField(IntegerField):
    def __init__(self, to_table):
        self.to_table = to_table
        super(ForeignKeyField, self).__init__()

    def create_sql(self):
        return '%s %s NOT NULL REFERENCES "%s" ("%s")' % (
            self.name, 'INTEGER', self.to_table, 'id'
        )


class MetaModel(type):
    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return super(MetaModel, cls).__new__(cls, name, bases, attrs)

        if 'Meta' not in attrs.keys() or not hasattr(attrs['Meta'], 'db_table'):
            attrs['tablename'] = name.lower()
        else:
            attrs['tablename'] = attrs['Meta'].db_table

        fields = {}
        has_primary_key = False
        for k, v in attrs.iteritems():
            if isinstance(v, Field):
                v.name = k
                fields[k] = v
                if isinstance(v, PrimaryKeyField):
                    has_primary_key = True

        for field in fields.keys():
            attrs.pop(field)

        if not has_primary_key:
            pk = PrimaryKeyField()
            pk.name = 'id'
            fields['id'] = pk

        attrs['fields'] = fields
        return super(MetaModel, cls).__new__(cls, name, bases, attrs)


class ModelException(Exception):
    pass


class Model(object):
    __metaclass__ = MetaModel

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            if k not in self.fields.keys():
                raise ModelException('Unknown column: {0}'.format(k))
            setattr(self, k, v)
        super(Model, self).__init__()

    @classmethod
    def get(cls, **kwargs):
        results = cls.filter(**kwargs)

        if len(results) != 1:
            raise ModelException('The count of results must equal to 1')
        return results

    @classmethod
    def filter(cls, **kwargs):
        base_query = 'select * from {tablename} where {where_sql};'
        where_list = []

        for k, v in kwargs.iteritems():
            if k not in cls.fields.keys():
                raise ModelException('Unknown column: {0}'.format(k))
            # where_list.append('{0}={1}'.format(k, cls.fields[k].sql_format(v)))
            where_list.append('{0}="{1}"'.format(k, str(v)))

        sql = base_query.format(
            tablename=cls.tablename,
            where_sql=' and '.join(where_list)
        )

        cursor = cls.db.execute(sql)
        cls.db.commit()
        results = cursor.fetchall()

        return results

    @staticmethod
    def first(results):
        # limit 1
        return results[0]

    @classmethod
    def select(cls, *args):
        return SelectQuery(cls, args)
    #
    # @classmethod
    # def update(cls, *args, **kwargs):
    #     return UpdateQuery(cls, args, **kwargs)
    #
    # @classmethod
    # def delete(cls, *args, **kwargs):
    #     return DeleteQuery(cls, args, **kwargs)

    def save(self):
        base_query = 'insert into {tablename}({columns}) values({items});'
        columns = []
        values = []
        for field_name, field_model in self.fields.iteritems():
            if hasattr(self, field_name):
                columns.append(field_name)
                values.append(field_model.sql_format(getattr(self, field_name)))

        sql = base_query.format(
            tablename=self.tablename,
            columns=', '.join(columns),
            items=', '.join(values)
        )

        self.db.execute(sql)
        self.db.commit()


class Sqlite(threading.local):

    def __init__(self, database):
        super(Sqlite, self).__init__()
        self.database = database
        self.conn = sqlite3.connect(self.database, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

        self.tables = {}
        setattr(self, 'Model', Model)
        setattr(self.Model, 'db', self)

    def create_all(self):
        for table_name, table_model in self.tables.items():
            if issubclass(table_model, self.Model):
                print("create table {0}.".format(table_name))
                self.create_table(table_model)

    def create_table(self, model):
        table_name = model.tablename
        create_sql = ', '.join(field.create_sql() for field in model.fields.values())

        cursor = self.conn.cursor()
        cursor.execute('create table {0} ({1});'.format(table_name, create_sql))

        if table_name not in self.tables.keys():
            self.tables[table_name] = model
        self.commit()

    def drop_table(self, model):
        table_name = model.tablename

        cursor = self.conn.cursor()
        cursor.execute('drop table {0};'.format(table_name))
        del self.tables[table_name]
        self.commit()

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    def execute(self, sql, commit=False):
        cursor = self.conn.cursor()
        cursor.execute(sql)
        if commit:
            self.commit()
        return cursor


class SelectQuery(object):
    """ select title, content from post where id = 1 and title = "my title";
        select title, content from post where id > 3;
    """

    def __init__(self, model, *args):
        self.base_sql = 'select {columns} from {tablename};'
        self.model = model
        self.query = list(*args) if args != ((),) else ['*']

    @property
    def sql(self):
        return self.base_sql.format(
            columns=', '.join([str(column) for column in self.query]),
            tablename=self.model.tablename
        )

    def all(self):
        return self._execute(self.sql)

    def first(self):
        sql = '{0} limit 1;'.format(self.sql.rstrip(';'))
        return self._execute(sql)[0]

    def where(self, *args, **kwargs):
        where_list = []
        for k, v in kwargs.iteritems():
            where_list.append('{0}="{1}"'.format(k, str(v)))
        where_list.extend(list(args))

        sql = '{0} where {1};'.format(self.sql.rstrip(';'), ' and '.join(where_list))
        return self._execute(sql)

    def _base_function(self, func):
        columns = ', '.join([str(column) for column in self.query])
        sql = self.base_sql.format(
                  columns='{0}({1})'.format(func, columns),
                  tablename=self.model.tablename
              )
        cursor = self.model.db.execute(sql)
        record = cursor.fetchone()
        return record[0]

    def count(self):
        return self._base_function('count')

    def max(self):
        """Person.select('id').max()"""
        return self._base_function('max')

    def min(self):
        return self._base_function('min')

    def avg(self):
        return self._base_function('avg')

    def sum(self):
        return self._base_function('sum')

    def _execute(self, sql):
        cursor = self.model.db.execute(sql)
        descriptor = list(i[0] for i in cursor.description)
        records = cursor.fetchall()
        query_set = [self._make_instance(descriptor, record) for record in records]
        return query_set

    def _make_instance(self, descriptor, record):
        # must handle empty case.
        try:
            instance = self.model(**dict(zip(descriptor, record)))
        except TypeError:
            return None
        return instance


if __name__ == '__main__':
    db = Sqlite('test.db')

    class Person(Model):
        id = PrimaryKeyField()
        name = CharField(max_lenth=20)
        age = IntegerField()
        create_time = DateTimeField()

        class Meta:
            db_table = 'test'

    # p = Person()
    # # db.create_table(p)
    # p.age = 12
    # p.name = 'test'
    # p.create_time = datetime.now()
    # p.save()
    # p2 = Person.get(id=1, name='test')
    # p = Person.select('id', 'name')
    # db.drop_table(p)
    # p = Person.select('id', 'name').first()
    # p = Person.select().where(id=1)[0]
    # p = Person.select().where('id<3', name='test')
    p = Person.select('name').max()
    print p
    # print p.id, p.name
    pass

