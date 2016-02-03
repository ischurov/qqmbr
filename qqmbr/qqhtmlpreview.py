# (c) Ilya V. Schurov, 2016
# Available under MIT license (see LICENSE file in the root folder)

from qqmbr.qqdoc import QqParser
from qqmbr.qqhtml import QqHTMLFormatter
import qqmbr.odebook
import os
import numpy
from flask import Flask, render_template, abort, send_from_directory
app = Flask(__name__, static_url_path='')

app.debug = True

@app.route('/fig/<path:path>')
def send_fig(path):
    return send_from_directory('fig', path)

@app.route("/<filename>")
def show_html(filename):
    path = os.path.join("samplefiles",filename)
    if not os.path.isfile(path):
        abort(404)
    with open(path) as f:
        lines = f.readlines()
    parser = QqParser()
    formatter = QqHTMLFormatter()
    parser.allowed_tags.update(formatter.uses_tags())
    tree = parser.parse(lines)
    formatter.root = tree
    formatter.pythonfigure_globals.update({'ob': qqmbr.odebook, 'np': numpy})
    html = formatter.do_format()
    print(html)
    print(tree.as_list())
    return render_template("preview.html", html=html, title=tree._h1.text_content, toc=formatter.mk_toc())

if __name__ == "__main__":
    app.run()