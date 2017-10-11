# (c) Ilya V. Schurov, 2016
# Available under MIT license (see LICENSE file in the root folder)

from indentml.parser import QqParser, QqTag
from qqmbr.qqhtml import QqHTMLFormatter
import qqmbr.odebook as odebook
import os
import numpy
from flask import (Flask, render_template, abort, send_from_directory,
                   url_for, g)
from subprocess import Popen, PIPE, STDOUT
from bs4 import BeautifulSoup
import hashlib
import itertools
import argparse
from flask_frozen import Freezer

scriptdir = os.path.dirname(os.path.realpath(__file__))
curdir = os.getcwd()

app = Flask(__name__, static_url_path='')

app.config['mjpage'] = os.path.join(
    scriptdir, '../third-party/node_modules/mathjax-node-page/bin/mjpage')

app.config['preamble'] = r"""
<div style='visibility: hidden; display: none;'>
\[
\newcommand{\ph}{\varphi}
\newcommand{\eps}{\varepsilon}
\newcommand{\padi}[2]{\frac{\partial #1}{\partial #2}}
\newcommand{\mb}{\mathbf}
\newcommand{\re}{\mathop{\mathrm{Re}}}
\newcommand{\im}{\mathop{\mathrm{Im}}}
\]
</div>
"""
app.config['mathjax_node'] = False
app.config['css_correction'] = r"""
<style type='text/css'>
.mjx-chtml {
font-size: 120%;
}
</style>
"""
app.config['MATHJAX_ALLTHEBOOK'] = False

app.debug = True
allthebook = None
app.config['FILE'] = None

class QqFlaskHTMLFormatter(QqHTMLFormatter):

    def __init__(self):
        super().__init__()
        self.figures_dir = os.path.join(curdir, "fig")

    def url_for_chapter_by_index(self, index):
        return url_for('show_chapter_by_index', index=index)

    def url_for_chapter_by_label(self, label):
        return url_for('show_chapter_by_label', label=label)

    def url_for_snippet(self, label):
        return url_for('show_snippet', label=label)

    def url_for_figure(self, s):
        return url_for('send_fig', path=s)

    def url_for_eq_snippet(self, number):
        return url_for('show_eq', number=number)


@app.route('/fig/<path:path>')
def send_fig(path):
    return send_from_directory(os.path.join(curdir, 'fig'), path)

@app.route('/assets/<path:path>')
def send_asset(path):
    return send_from_directory(os.path.join(scriptdir, 'assets'), path)

@app.route("/eq/<number>/")
def show_eq(number):
    if allthebook is None:
        abort(404)

    soup = BeautifulSoup(allthebook, 'html.parser')
    anchor = soup.find(id="mjx-eqn-" + str(number))
    if not anchor:
        print("[mjx-eqn-" + str(number) + "not found]")
        return "[mjx-eqn-" + str(number) + "not found]"
    tag = anchor.find_parent(class_='mjx-chtml')
    return str(tag)

#@app.route("/allthebook/")
def show_allthebook():
    if allthebook is None:
        abort(404)

    return render_template("preview.html", html=allthebook)

def prepare_book():
    path = os.path.join(curdir, app.config['FILE'])
    if not os.path.isfile(path):
        abort(404)
    with open(path) as f:
        lines = f.readlines()
    parser = QqParser()
    formatter = QqFlaskHTMLFormatter()

    parser.allowed_tags.update(formatter.uses_tags())
    parser.allowed_tags.add('idx') # for indexes
    tree = parser.parse(lines).process_include_tags(parser, curdir)
    formatter.root = tree
    formatter.pythonfigure_globals.update({'ob': odebook, 'np': numpy})
    formatter.code_prefixes['pythonfigure'] += ("import numpy as np\n"
                                            "import qqmbr.odebook as ob\n"
                                            "# see https://github.com/ischurov/qqmbr/blob/master/qqmbr/odebook.py"
                                            "\n\n")

    formatter.plotly_globals.update({'np': numpy})
    formatter.code_prefixes['plotly'] = formatter.code_prefixes.get('plotly',"") + "import numpy as np\n\n"

    formatter.mode = 'bychapters'
    formatter.make_numbers(tree)
    formatter.mk_chapters()

    # dirty hack to get equation snippet work
    global allthebook
    if allthebook is None:
        if app.config.get("MATHJAX_ALLTHEBOOK"):
            style, allthebook = mathjax(app.config.get('preamble', '') + formatter.format(tree))
        else:
            allthebook = formatter.format(tree)
            style = ""
        app.config['css_correction'] = style + app.config.get('css_correction')

    return tree, formatter

def show_chapter(index=None, label=None):
    print("Processing chapter index = {}, label = {}".format(index, label))

    tree, formatter = prepare_book()

    if index is None and label is None:
        index = min(1, len(formatter.chapters) - 1)

    if index is None:
        index = formatter.label_to_chapter[label]
    #for x in formatter.chapters[index].content:
    #    if isinstance(x, QqTag):
    #        print(x.as_list())
    #    else:
    #        print(x)

    html = formatter.format(formatter.chapters[index].content,
                            blanks_to_pars=True)

    if index == len(formatter.chapters) - 1:
        next = None
    else:
        next = formatter.url_for_chapter(index=index + 1)

    if index <= 1:
        prev = None
    else:
        prev = formatter.url_for_chapter(index=index - 1)

    style, body = mathjax_if_needed(html)

    style += "\n".join(itertools.chain(formatter.css.values(),
                                       formatter.js_top.values()))

    html = style + app.config.get('css_correction', '') + body

    ftoc = formatter.format_toc(formatter.extract_toc(maxlevel=1),
                                fromchapter=index)

    curftoc = formatter.format_toc(formatter.extract_toc(
        maxlevel=3).children[index], fromchapter=index, tochapter=index)

    chapter_heading = formatter.chapters[index].heading
    # print(formatter.chapters[index].content)
    return render_template("preview.html",
                           meta=tree.find("meta"),
                           html=html,
                           title=(chapter_heading.text_content),
                           ftoc=ftoc,
                           curftoc=curftoc,
                           preamble="",
                           next=next, prev=prev,
                           js_bottom = "\n".join(
                               formatter.js_bottom.values()),
                           js_onload = "\n".join(
                               formatter.js_onload.values()))

@app.route("/chapter/index/<int:index>/")
def show_chapter_by_index(index=None):
    return show_chapter(index=index)

@app.route("/chapter/label/<label>/")
def show_chapter_by_label(label):
    return show_chapter(label=label)

@app.route("/snippet/<label>/")
def show_snippet(label):
    tree, formatter = prepare_book()
    tag = formatter.label_to_tag.get(label)

    if tag is None or tag.name != 'snippet':
        abort(404)
    if tag.exists("backref"):
        backref = tag.backref_.value
    else:
        backref = label

    parser = QqParser()
    parser.allowed_tags.update(formatter.uses_tags())
    backref_tag = parser.parse(r"\ref[Подробнее\nonumber][{}]".format(backref))
    tag.append_child(backref_tag.ref_)

    html = formatter.format(tag, blanks_to_pars=True)

    return mathjax_if_needed(html)[1]
@app.route("/")
def show_default():
    return show_chapter_by_index()

def mathjax_if_needed(s):
    preamble = app.config.get('preamble', '')
    if not app.config.get('mathjax_node'):
        return "", preamble + s
    return mathjax(preamble + s)

def mathjax(s):
    with open("temp.log", "w") as f:
        f.write(s)

    p = Popen([app.config['mjpage'],
              '--dollars',
               '--output', "CommonHTML",
               '--fontURL',
               ("https://cdnjs.cloudflare.com/ajax/libs/"
                "mathjax/2.7.0/fonts/HTML-CSS")], stdout=PIPE, stdin=PIPE,
              stderr=PIPE)

    #filename = hashlib.sha256(s.encode('utf-8')).hexdigest()
    #with open(filename, 'w') as f:
    #    print(s, file=f)

    res = p.communicate(input=s.encode('utf-8'))
    out = res[0].decode('utf-8')
    err = res[1].decode('utf-8')

    soup = BeautifulSoup(out, 'html.parser')
    style = str(soup.style)
    body = "".join(str(s) for s in soup.body.children)

    return style, body

commands = {}

def register_command(f):
    commands[f.__name__] = f
    return f

@register_command
def preview():
    app.run(host='0.0.0.0')

@register_command
def build():
    app.config['mathjax_node'] = True

    freezer = Freezer(app)
    app.config['FREEZER_BASE_URL'] = 'http://math-info.hse.ru/odebook/'
    app.config['MATHJAX_ALLTHEBOOK'] = True
    app.config['FREEZER_DESTINATION'] = os.path.join(curdir, "build")
    freezer.freeze()

@register_command
def convert():
    path = os.path.join(curdir, app.config['FILE'])
    with open(path) as f:
        lines = f.readlines()

    formatter = QqHTMLFormatter()
    parser = QqParser(allowed_tags=formatter.uses_tags())

    tree = None
    try:
        tree = parser.parse(lines)
    except Exception as e:
        print("Parse error:", str(e))
        raise

    formatter.root = tree
    try:
        output = formatter.do_format()
    except Exception as e:
        print("Formatting error:", str(e))
        raise
    print(output)

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("command",
                           help="command to invoke: preview or build")
    argparser.add_argument("file",
                           help="File to proceed",
                           default="index.qq",
                           nargs='?')
    args = argparser.parse_args()
    app.config['FILE'] = args.file
    if args.command in commands:
        commands[args.command]()
    else:
        print("Unkown command " + args.command)

if __name__ == "__main__":
    preview()
