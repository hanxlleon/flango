import unittest
from datetime import datetime

from flango import database

from models import Author, Post, Tag


db = database.Sqlite('flango.db')


class BaseTests(unittest.TestCase):
    def setUp(self):
        db.create_table(Author)
        db.create_table(Post)

        for i in range(1, 6):
            db.execute('insert into {tablename}({columns}) values({items});'.format(
                tablename='author',
                columns='name',
                items='"test author {0}"'.format(str(i))
            ))
            db.execute('insert into {tablename}({columns}) values({items});'.format(
                tablename='my_post',
                columns='title, content, author_id',
                items='"test title {0}", "test content {0}", {0}'.format(str(i))
            ))

    def tearDown(self):
        db.drop_table(Author)
        db.drop_table(Post)

    def test_create_table(self):
        pass

    def test_drop_table(self):
        pass

    def test_roll_back(self):
        pass

    def test_close(self):
        pass

    def test_execute(self):
        pass

    def test_commit(self):
        pass

    def test_init(self):
        init_dict = {
            'author': Author,
            'my_post': Post,
        }

        self.assertEqual(init_dict, db.tables)


class QueryTests(BaseTests):

    def test_save_and_insert(self):
        author = Author(name='test author 6')
        author.save()

        post = Post(title='test title 6', content='test content 6', pub_date=datetime.now(), author_id='6')
        post.save()

        c = db.execute('select * from author where id=6;')
        self.assertEqual(len(c.fetchall()), 1)
        c = db.execute('select * from my_post where id=6;')
        self.assertEqual(len(c.fetchall()), 1)

    def test_get(self):
        p1 = Post.get(id=1)
        self.assertEqual(p1.title, 'test title 1')
        self.assertEqual(p1.content, 'test content 1')
        self.assertEqual(p1.id, 1)

    def test_select(self):
        p1 = Post.select('*').where(id=2).all()
        self.assertEqual(len(p1), 1)
        self.assertEqual(p1[0].id, 2)

        p2 = Post.select('id', 'content').where(id=2).all()
        self.assertEqual(len(p1), 1)
        self.assertEqual(p2[0].id, 2)
        self.assertEqual(p2[0].content, 'test content 2')

        p3 = Post.select().where("id < 5").all()
        self.assertEqual(len(p3), 4)
        self.assertEqual([1, 2, 3, 4], [i.id for i in p3])

        p4 = Post.select().first()
        self.assertEqual(p4.id, 1)

    def test_delete(self):
        p1 = Post.delete(id=1).commit()
        self.assertEqual(p1.rowcount, 1)
        p2 = Post.delete(id=1).commit()
        self.assertEqual(p2.rowcount, 0)
        p3 = Post.delete('id < 3').commit()
        self.assertEqual(p3.rowcount, 1)

    def test_update(self):
        p1 = Post.update(id=5).set(title="new title 5").commit()
        self.assertEqual(p1.rowcount, 1)
        p2 = Post.get(id=5)
        self.assertEqual(p2.title, 'new title 5')
        p3 = Post.update(id=-1).set(title="unexisted id").commit()
        self.assertEqual(p3.rowcount, 0)

    def test_foreignkeyfields(self):
        posts = Author.get(id=5).posts.all()
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].id, 5)

    def test_orderby(self):
        posts = Post.select().orderby('id', 'asc').all()
        self.assertEqual([p.id for p in posts], [1, 2, 3, 4, 5])
        posts = Post.select().orderby('id', 'desc').all()
        self.assertEqual([p.id for p in posts], [5, 4, 3, 2, 1])

    def test_like(self):
        posts = Post.select().where('content').like("test%").all()
        self.assertEqual([p.id for p in Post.select().all()], [i.id for i in posts])
        posts = Post.select().where('id').like("1").all()
        self.assertEqual([Post.get(id=1).id], [p.id for p in posts])
        posts = Post.select().where('content').like('%est%').all()
        self.assertEqual([p.id for p in Post.select().all()], [i.id for i in posts])


class ManytoManyFieldsTest(BaseTests):

    def test_mtom_append(self):
        p = Post.get(id=1)
        t1 = Tag.get(id=1)
        t2 = Tag.get(id=2)
        p.tags.append(t1)
        p.tags.append(t2)
        self.assertEqual([p.id for p in p.tags.all()], [t1.id, t2.id])
        self.assertEqual([p.id for p in t1.posts.all()], [p.id])
        self.assertEqual([p.id for p in t2.posts.all()], [p.id])

    def test_mtom_remove(self):
        p = Post.get(id=5)
        self.assertEqual(p.tags.all(), [])
        t = Tag.get(id=5)
        p.tags.append(t)
        self.assertEqual([t.id for t in p.tags.all()], [t.id])
        self.assertEqual([p.id for p in t.posts.all()], [p.id])
        p.tags.remove("tag_id=5")
        self.assertEqual(p.tags.all(), [])
        self.assertEqual(t.posts.all(), [])

    def test_mtom_count(self):
        p = Post.get(id=3)
        self.assertEqual(p.tags.count(), 0)
        p.tags.append(Tag.get(id=3))
        p.tags.append(Tag.get(id=4))
        self.assertEqual(p.tags.count(), 2)


class FunctionTests(BaseTests):
    def test_count(self):
        c1 = Post.select().count()
        self.assertEqual(c1, 5)
        c2 = Post.select().where('id>3').count()
        self.assertEqual(c2, 2)

    def test_max(self):
        c1 = Post.select('id').max()
        self.assertEqual(c1, 5)
        c2 = Post.select('id').where('id < 3').max()
        self.assertEqual(c2, 2)
        c3 = Post.select('id').where('id > 10').max()
        self.assertEqual(c3, None)

    def test_min(self):
        c1 = Post.select('id').min()
        self.assertEqual(c1, 1)

    def test_avg(self):
        c1 = Post.select('id').avg()
        self.assertEqual(c1, 3)

    def test_sum(self):
        c1 = Post.select('id').sum()
        self.assertEqual(c1, 15)


if __name__ == '__main__':
    unittest.main()