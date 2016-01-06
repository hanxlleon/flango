# -*- coding: utf-8 -*-
from flango import database
from . import db


class Comment(db.Model):
    id = database.PrimaryKeyField()
    title = database.CharField(100)
    content = database.CharField(400)
    pub_date = database.DateTimeField()

    post_id = database.ForeignKeyField('post')

    def __repr__(self):
        return '<Comment {0}>'.format(self.title)


class Post(db.Model):
    id = database.PrimaryKeyField()
    title = database.CharField(100)
    content = database.TextField()
    pub_date = database.DateTimeField()

    comments = database.ForeignKeyReverseField('comment')

    class Meta:
        __tablename__ = 'post'

    def __repr__(self):
        return '<Post {0}>'.format(self.title)


class Tag(db.Model):
    id = database.PrimaryKeyField()
    name = database.CharField(100)

    posts = database.ManyToManyField(Post)

    def __repr__(self):
        return '<Tag {0}>'.format(self.name)


# db.create_table(Comment)
# db.create_table(Post)
# db.create_table(Tag)