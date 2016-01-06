from datetime import datetime
from . import app
from .models import Comment, Post, Tag
from .renderer import md_renderer


@app.route('/')
def index():
    posts = Post.select().all()
    return app.render('index.html', posts=posts)


def tag_filter(tags):
    filter_tags = tags.strip().split(' ')
    existed_tags = Tag.select().all()
    tag_names = set([tag.name for tag in existed_tags])
    for filter_tag in filter_tags:
        if filter_tag not in tag_names:
            Tag(name=filter_tag).save()
    return [tag for tag in Tag.select().all() if tag.name in set(filter_tags)]


@app.route('/new_post', methods=['POST', 'GET'])
def create_post():
    if app.request.method == 'GET':
        return app.render("editor.html")

    title = app.request.forms['title']
    tags = tag_filter(app.request.forms['tag'])
    content = app.request.forms['editor']
    post = Post(title=title, content=content, pub_date=datetime.now())
    post.save()

    for tag in tags:
        post.tags.add(tag)

    return app.redirect(app.url_for(show_post, id=post.id))


@app.route('/post/<int:id>')
def show_post(id):
    post = Post.get(id=id)
    post.content = md_renderer.render(post.content)
    return app.render('post.html', post=post)


@app.route('/tag/<int:id>')
def show_tag(id):
    tag = Tag.get(id=id)
    return app.render('tag.html', tag=tag)


@app.route('/new_comment', methods=['POST'])
def create_comment():
    post_id = app.request.forms['post_id']
    title = app.request.forms['title']
    content = app.request.forms['content']

    comment = Comment(title=title, content=content, pub_date=datetime.now(), post_id=post_id)
    comment.save()

    return app.redirect(app.url_for(show_post, id=post_id))


