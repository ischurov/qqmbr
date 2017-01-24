from flask_frozen import Freezer

from qqbook.qqhtmlpreview import app

app.config['mathjax_node'] = True

freezer = Freezer(app)
app.config['FREEZER_BASE_URL'] = 'http://math-info.hse.ru/odebook/'
app.config['MATHJAX_ALLTHEBOOK'] = True

if __name__ == '__main__':
    freezer.freeze()
