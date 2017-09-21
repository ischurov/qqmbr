# (c) Ilya V. Schurov, 2016
# Available under MIT license (see LICENSE file in the root folder)

from indentml.parser import QqParser, QqTag
from qqmbr.qqhtml import QqHTMLFormatter
from flask import (Flask, render_template, abort, send_from_directory,
                   url_for, g, request, jsonify, redirect)
import os
import requests
import re

app = Flask(__name__, static_url_path='')
app.config["APPLICATION_ROOT"] = "/"

app.debug=True

scriptdir = os.path.dirname(os.path.realpath(__file__))

prefixes = [
    ('https://gist.github.com/', 'gist/',
     'https://gist.githubusercontent.com/'),
    ('https://', 'https/', 'https://'),
    ('http://', 'http/', 'http://')
]


def url_to_path(url):
    for url_prefix, path_prefix, _ in prefixes:
        if re.match(url_prefix, url):
            url = re.sub(url_prefix, path_prefix, url, count=1)
            break
    return url

def path_to_url(path):
    for url_prefix, path_prefix, _ in prefixes:
        if re.match(path_prefix, path):
            path = re.sub(path_prefix, url_prefix, path, count=1)
            break
    return path


def path_to_source_url(path):
    for _, path_prefix, url_prefix in prefixes:
        if re.match(path_prefix, path):
            path = re.sub(path_prefix, url_prefix, path, count=1)
            if path_prefix == 'gist/':
                path = path.rstrip('/') + '/raw'
            break
    return path

@app.route('/assets/<path:path>')
def send_asset(path):
    return send_from_directory(os.path.join(scriptdir, 'assets'), path)

@app.route('/get/<path:path>')
def render(path):
    print(path_to_source_url(path))
    r = requests.get(path_to_source_url(path))
    r.encoding = 'UTF-8'
    if not r:
        abort(500)

    formatter = QqHTMLFormatter(with_chapters=False)

    formatter.localnames = {}

    parser = QqParser(allowed_tags=formatter.safe_tags)
    try:
        tree = parser.parse(r.text)
    except Exception as e:
        if app.debug:
            raise e
        return render_template("error.html",
                               error='parse error: ' + str(e)), 400

    formatter.root = tree
    try:
        output = formatter.do_format()
    except Exception as e:
        if app.debug:
            raise e
        return render_template("error.html",
                               error='format error: ' + str(e)), 400

    meta = tree.find_or_empty("meta")
    print(meta.as_list())

    return render_template("render_url.html", output=output,
                           source_url=path_to_url(path),
                           meta=meta)

@app.route('/', methods=['GET', 'POST'])
def showform():
    if request.method == 'GET':
        return render_template("render_form.html",
                               rootdir=app.config["APPLICATION_ROOT"])
    else:
        url = request.form.get('url')
        return redirect(url_for("render", path=url_to_path(url)))


if __name__ == '__main__':
    app.run()