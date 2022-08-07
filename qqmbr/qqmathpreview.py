# (c) Ilya V. Schurov, 2016
# Available under MIT license (see LICENSE file in the root folder)

from indentml.parser import QqParser, QqTag
from qqmbr.qqhtml import QqHTMLFormatter
from flask import (Flask, render_template, abort, send_from_directory,
                   url_for, g, request, jsonify)
import os

app = Flask(__name__, static_url_path='')
app.config["APPLICATION_ROOT"] = "/qqmathpreview"

app.debug=True

scriptdir = os.path.dirname(os.path.realpath(__file__))


@app.route('/assets/<path:path>')
def send_asset(path):
    return send_from_directory(os.path.join(scriptdir, 'assets'), path)

@app.route('/render', methods=['GET', 'POST'])
def render():
    text = request.values.get('text', '').replace('\r\n', '\n')
    formatter = QqHTMLFormatter()

    formatter.localnames = {}

    parser = QqParser(allowed_tags=formatter.safe_tags)
    try:
        tree = parser.parse(text)
    except Exception as e:
        return jsonify(error='parse error: ' + str(e))

    formatter.root = tree
    try:
        output = formatter.do_format()
    except Exception as e:
        return jsonify(error='format error: ' + str(e))
    return jsonify(output=output)

@app.route('/')
def showform():
    return render_template("preview_form.html",
                           rootdir=app.config["APPLICATION_ROOT"])


if __name__ == '__main__':
    app.run()