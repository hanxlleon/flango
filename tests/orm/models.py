from flango import database


# class Post_Tag_Relate(database.Model):
#
#     """
#     Many to many relationship test.
#     """
#     id = database.PrimaryKeyField()
#     my_post_id = database.ForeignKeyField('my_post')
#     tag_id = database.ForeignKeyField('tag')
#
#     def __repr__(self):
#         return '<Relation table post_id = {0}, tag_id = {1}>'.format(self.post_id, self.tag_id)


class Post(database.Model):
    title = database.CharField(max_lenth=100)
    content = database.TextField()
    pub_date = database.DateTimeField()

    author_id = database.ForeignKeyField('author')

    class Meta:
        db_table = 'my_post'

    def __repr__(self):
        return '<Post {0}>'.format(self.title)


class Author(database.Model):
    id = database.PrimaryKeyField()
    name = database.CharField(max_lenth=20)

    posts = database.ForeignKeyReverseField('my_post')

    def __repr__(self):
        return '<Author {0}>'.format(self.name)


class Tag(database.Model):
    id = database.PrimaryKeyField()
    name = database.CharField(100)

    posts = database.ManyToManyField(Post)

    def __repr__(self):
        return '<Tag {0}>'.format(self.name)