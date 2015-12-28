

class Field(object):
    name = ''

    @property
    def sql(self):
        raise NotImplementedError


class IntegerField(Field):

    @property
    def sql(self):
        return '"{0}" {1}'.format(self.name, 'INTEGER')


class CharField(Field):
    def __init__(self, max_lenth=255):
        self.max_lenth = max_lenth

    @property
    def sql(self):
        return '"{0}" {1}({2})'.format(self.name, 'VARCHAR', self.max_lenth)


class MetaModel(type):
    def __new__(cls, name, bases, attrs):
        cls = super(MetaModel, cls).__new__(cls, name, bases, attrs)
        # fields
        fields = {}
        refed_fields = {}
        cls_dict = cls.__dict__
        if '__tablename__' in cls_dict.keys():
            setattr(cls, '__tablename__', cls_dict['__tablename__'])
        else:
            setattr(cls, '__tablename__', cls.__name__.lower())

        if hasattr(cls, 'db'):
            getattr(cls, 'db').__tabledict__[cls.__tablename__] = cls

        has_primary_key = False
        setattr(cls, 'has_relationship', False)
        for name, attr in cls.__dict__.items():
            if isinstance(attr, ForeignKeyReverseField) or isinstance(attr, ManyToManyField):
                setattr(cls, 'has_relationship', True)
                attr.update(name, cls.__tablename__, cls.db)
                refed_fields[name] = attr
            if isinstance(attr, Field):
                attr.name = name
                fields[name] = attr
                if isinstance(attr, PrimaryKeyField):
                    has_primary_key = True

        if not has_primary_key:
            pk = PrimaryKeyField()
            pk.name = 'id'
            fields['id'] = pk
        setattr(cls, '__fields__', fields)
        setattr(cls, '__refed_fields__', refed_fields)
        return cls

class Model(object):
    __metaclass__ = MetaModel

    def __init__(self):
        print self
        pass



if __name__ == '__main__':
    class Person(Model):
        name = CharField(max_lenth=20)
        age = IntegerField()

        __tablename__ = 'test'

    p = Person()
    pass

