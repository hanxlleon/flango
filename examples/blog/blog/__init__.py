from flango import flango
from flango import database

app = flango.Flango('blog')
app.config['DATABASE_NAME'] = 'blog.db'

db = database.Sqlite(app.config['DATABASE_NAME'])

from . import views
