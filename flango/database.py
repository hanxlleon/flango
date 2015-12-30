# coding: utf-8
import sqlite3
import threading


class Field(object):
    def __init__(self, column_type):
        self.column_type = column_type
        self.name = None

    def create_sql(self):
        return '"{0}" {1}'.format(self.name, self.column_type)


class IntegerField(Field):
    def __init__(self):
        super(IntegerField, self).__init__('INTEGER')

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


class TextField(Field):
    def __init__(self):
        super(TextField, self).__init__('TEXT')

    def sql_format(self, data):
        return '"{0}"'.format(str(data))


class DateTimeField(Field):
    def __init__(self):
        super(DateTimeField, self).__init__('DATETIME')

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


class ForeignKeyReverseField(object):

    def __init__(self, from_table):
        self.from_table = from_table
        self.name = None
        self.tablename = None
        self.id = None
        self.db = None
        self.from_model = None
        self.relate_column = None

    def update(self, name, tablename, db):
        self.name = name
        self.tablename = tablename
        self.db = db
        self.from_model = self.db.tables[self.from_table]
        for k, v in self.from_model.__dict__.iteritems():
            if isinstance(v, ForeignKeyField) and v.to_table == self.tablename:
                self.relate_column = k

    def all(self):
        return self.from_model.select('*').where('='.join([self.relate_column, str(self.id)])).all()

    def count(self):
        return self.from_model.select('*').where('='.join([self.relate_column, str(self.id)])).count()


class ManyToManyField(object):
    def __init__(self, relate_table, to_table):
        self.relate_table = relate_table
        self.to_table = to_table

        self.name = None
        self.tablename = None
        self.id = None
        self.db = None

        self.relate_model = None
        self.relate_column = None

    def update(self, name, tablename, db):
        self.name = name
        self.tablename = tablename
        self.db = db
        self.relate_model = self.db.tables[self.relate_table]
        # self.to_model = self.db.tables[self.to_table]
        self.relate_column = '{0}_id'.format(self.tablename)
        self.opposite_column = '{0}_id'.format(self.to_table)

    def add(self, instance):
        insert = {
            self.relate_column: self.id,
            self.opposite_column: instance.id
        }
        self.relate_model(**insert).save()

    def remove(self, instance):
        self.relate_model.delete(**{self.opposite_column: instance.id}).commit()

    def all(self):
        self.to_model = self.db.tables[self.to_table]

        opposite_instances = self.relate_model.select().where(**{self.relate_column: self.id}).all()
        id_list = [getattr(instance, self.opposite_column) for instance in opposite_instances]
        return [self.to_model.get(id=opposite_id) for opposite_id in id_list]

    def count(self):
        return len(self.all())


class MetaModel(type):
    def __new__(mcs, name, bases, attrs):
        if name == 'Model':
            return super(MetaModel, mcs).__new__(mcs, name, bases, attrs)

        cls = super(MetaModel, mcs).__new__(mcs, name, bases, attrs)

        if 'Meta' not in attrs.keys() or not hasattr(attrs['Meta'], 'db_table'):
            setattr(cls, 'tablename', name.lower())
        else:
            setattr(cls, 'tablename', attrs['Meta'].db_table)

        if hasattr(cls, 'db'):
            getattr(cls, 'db').tables[cls.tablename] = cls

        fields = {}
        refed_fields = {}
        has_primary_key = False
        for field_name, field in cls.__dict__.items():
            if isinstance(field, ForeignKeyReverseField) or isinstance(field, ManyToManyField):
                field.update(field_name, cls.tablename, cls.db)
                refed_fields[field_name] = field
            if isinstance(field, Field):
                field.name = field_name
                fields[field_name] = field
                if isinstance(field, PrimaryKeyField):
                    has_primary_key = True

        for field in fields.keys() or refed_fields.keys():
            attrs.pop(field)

        if not has_primary_key:
            pk = PrimaryKeyField()
            pk.name = 'id'
            fields['id'] = pk

        setattr(cls, 'fields', fields)
        setattr(cls, 'refed_fields', refed_fields)

        return cls


class ModelException(Exception):
    pass


class Model(object):
    __metaclass__ = MetaModel

    def __init__(self, **kwargs):
        for name, field in kwargs.iteritems():
            if name not in self.fields.keys():
                raise ModelException('Unknown column: {0}'.format(name))
            setattr(self, name, field)

        super(Model, self).__init__()

    @classmethod
    def get(cls, **kwargs):
        return SelectQuery(cls).where(**kwargs).first()

    @classmethod
    def select(cls, *args):
        return SelectQuery(cls, args)

    @classmethod
    def update(cls, *args, **kwargs):
        return UpdateQuery(cls, *args, **kwargs)

    @classmethod
    def delete(cls, *args, **kwargs):
        return DeleteQuery(cls, args, **kwargs)

    def save(self):
        base_query = 'insert into {tablename}({columns}) values({items});'
        columns = []
        values = []
        for field_name, field_model in self.fields.iteritems():
            if hasattr(self, field_name) and not isinstance(getattr(self, field_name), Field):
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


class QueryException(Exception):
    pass


class SelectQuery(object):
    """ select title, content from post where id = 1 and title = "my title";
        select title, content from post where id > 3;
    """

    def __init__(self, model, *args):
        self.model = model
        self.base_sql = 'select {columns} from {tablename};'

        query_args = list(*args) if list(*args) else ['*']
        self.query = ', '.join([str(column) for column in query_args])

    @property
    def sql(self):
        return self.base_sql.format(
            columns=self.query,
            tablename=self.model.tablename
        )

    def all(self):
        return self._execute(self.sql)

    def first(self):
        self.base_sql = '{0} limit 1;'.format(self.base_sql.rstrip(';'))
        return self._execute(self.sql)[0]

    def where(self, *args, **kwargs):
        where_list = []
        for k, v in kwargs.iteritems():
            where_list.append('{0}="{1}"'.format(k, str(v)))
        where_list.extend(list(args))

        self.base_sql = '{0} where {1};'.format(self.base_sql.rstrip(';'), ' and '.join(where_list))
        return self

    def _base_function(self, func):
        sql = self.base_sql.format(
            columns='{0}({1})'.format(func, self.query),
            tablename=self.model.tablename
        )
        cursor = self.model.db.execute(sql)
        record = cursor.fetchone()
        return record[0]

    def count(self):
        return self._base_function('count')

    def max(self):
        """
        Post.select('id').max()
        """
        return self._base_function('max')

    def min(self):
        return self._base_function('min')

    def avg(self):
        return self._base_function('avg')

    def sum(self):
        return self._base_function('sum')

    def orderby(self, column, order):
        """
        Post.select().orderby('id', 'desc').all()
        """
        self.base_sql = '{0} order by {1} {2};'.format(self.base_sql.rstrip(';'), column, order)
        return self

    def like(self, pattern):
        """
        Post.select('id').where('content').like('%cont%')
        """
        if 'where' not in self.base_sql:
            raise QueryException('Like query must have a where clause before')

        self.base_sql = '{0} like "{1}";'.format(self.base_sql.rstrip(';'), pattern)
        return self

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

        for name, field in instance.refed_fields.iteritems():
            if isinstance(field, ForeignKeyReverseField) or isinstance(field, ManyToManyField):
                field.id = instance.id

        return instance


class UpdateQuery(object):
    def __init__(self, model, *args, **kwargs):
        self.model = model
        self.base_sql = 'update {tablename} set {update_columns};'
        self.update_list = []
        self.where_list = list(*args)
        for k, v in kwargs.iteritems():
            self.where_list.append('{0}="{1}"'.format(k, v))

        if self.where_list:
            self.base_sql = '{0} where {1}'.format(self.base_sql.rstrip(';'), ' and '.join(self.where_list))

    def set(self, **kwargs):
        for k, v in kwargs.iteritems():
            self.update_list.append('{0}="{1}"'.format(k, v))
        return self

    @property
    def sql(self):
        return self.base_sql.format(
            tablename=self.model.tablename,
            update_columns=' and '.join(self.update_list)
        )

    def commit(self):
        return self.model.db.execute(self.sql, commit=True)


class DeleteQuery(object):
    def __init__(self, model, *args, **kwargs):
        self.model = model
        self.sql = 'delete from {0};'.format(self.model.tablename)
        where_list = list(*args)
        for k, v in kwargs.iteritems():
            where_list.append('{0}="{1}"'.format(k, v))

        if where_list:
            self.sql = '{0} where {1}'.format(self.sql.rstrip(';'), ' and '.join(where_list))

    def commit(self):
        return self.model.db.execute(self.sql, commit=True)

if __name__ == '__main__':
   pass