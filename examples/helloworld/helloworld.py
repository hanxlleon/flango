from flango import flango


app = flango.Flango('/')


@app.route('/hello/<name>')
def hello(name):
    return 'Hello {0}!'.format(name)

app.run(DEBUG=True)
