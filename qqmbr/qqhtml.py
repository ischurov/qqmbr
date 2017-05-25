# (c) Ilya V. Schurov, 2016
# Available under MIT license (see LICENSE file in the root folder)

from indentml.parser import QqTag
from yattag import Doc
from collections import namedtuple
import re
import inspect
import hashlib
import os
import urllib.parse
from mako.template import Template
from fuzzywuzzy import process

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt

def mk_safe_css_ident(s):
    # see http://stackoverflow.com/a/449000/3025981 for details
    s = re.sub(r"[^a-zA-Z\d_-]", "_", s)
    if re.match(r"([^a-zA-Z]+)", s):
        m = re.match(r"([^a-zA-Z]+)", s)
        first = m.group(1)
        s = s[len(first):] + "__" + first
    return s

# FROM http://stackoverflow.com/a/14364249/3025981

def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise

# END FROM

class Counter():
    """
    Very simple class that support latex-style counters with subcounters.
    For example, if new section begins, the enumeration of subsections resets.
    If `showparents` option is set, str(counter) contains numbers of all its parents
    That's all.
    """

    def __init__(self, showparents=True):
        self.value = 0
        self.children = []
        self.parent = None
        self.showparents = showparents

    def reset(self):
        self.value = 0
        for child in self.children:
            child.reset()

    def increase(self):
        self.value += 1
        for child in self.children:
            child.reset()

    def spawn_child(self):
        newcounter = Counter()
        newcounter.parent = self
        self.children.append(newcounter)
        return newcounter

    def __str__(self):
        my_str = str(self.value)
        if self.parent and self.showparents:
            my_str = str(self.parent) + "." + my_str
        return my_str

def join_nonempty(*args, sep=" "):
    return sep.join(x for x in args if x)

Chapter = namedtuple('Chapter', ('header', 'content'))
plotly = None

class PlotlyPlotter(object):
    _first = True
    def __init__(self):

        self.buffer = []

    def plot(self, figure_or_data):
        self.buffer.append(
            plotly.offline.plot(figure_or_data, show_link=False, validate=True,
                                output_type='div', include_plotlyjs=False)
        )
        PlotlyPlotter._first = False

    def get_data(self):
        ret = "".join(self.buffer)
        self.buffer.clear()
        return ret


def rstrip_p(s: str) -> str:
    return re.sub(r"(\s*</?p>\s*)+$", "", s)


class QqHTMLFormatter(object):

    def __init__(self, root: QqTag=None):

        self.templates_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "templates")

        self.label2number = {}
        self.label2title = {}
        self.label2tag = {}
        self.label2chapter = {}
        self.flabel2tag = {}
        self.root = root
        self.counters = {}
        self.chapters = []


        self.mode = 'wholedoc'
        #: how to render the doc? the following options are available:
        #: - 'wholedoc' - the whole document on one page
        #: - 'bychapters' - every chapter on its own page

        self.counters['h1'] = Counter()
        self.counters['h2'] = self.counters['h1'].spawn_child()
        self.counters['h3'] = self.counters['h2'].spawn_child()
        self.counters['h4'] = self.counters['h3'].spawn_child()

        self.counters['equation'] = self.counters['h1'].spawn_child()
        self.counters['equation'].showparents = True
        self.counters['item'] = {'align': self.counters['equation']}
        self.counters['figure'] = self.counters['h1'].spawn_child()

        self.enumerateable_envs = {name: name.capitalize() for name in ['remark', 'theorem', 'example', 'exercise',
                                                                        'definition', 'proposition', 'lemma',
                                                                        'question', 'corollary']}

        # You can make self.localnames = {} to use plain English localization

        self.localnames = {
            'Remark': 'Замечание',
            'Theorem': 'Теорема',
            'Example': 'Пример',
            'Exercise': 'Упражнение',
            'Definition': 'Определение',
            'Proposition': 'Утверждение',
            'Lemma': 'Лемма',
            'Proof': 'Доказательство',
            'Proof outline': 'Набросок доказательства',
            'Figure': 'Рисунок',
            'Fig.': "Рис.",
            'Question': 'Вопрос',
            'Corollary': 'Следствие',
        }

        self.formulaenvs = {'eq', 'equation', 'align'}

        for env in self.enumerateable_envs:
            self.counters[env] = self.counters['h1'].spawn_child()
            self.counters[env].showparents = False

        self.figures_dir = None

        self.default_figname = "fig"

        plt.rcParams['figure.figsize'] = (6, 4)

        self.pythonfigure_globals = {'plt': plt}
        self.code_prefixes = {'pythonfigure': 'import matplotlib.pyplot as plt\n',
                              'plotly': ("import plotly\n"
                                        "import plotly.graph_objs as go\n"
                                        "from plotly.offline import iplot as plot\n"
                                        "from plotly.offline import init_notebook_mode\n\n"
                                        "init_notebook_mode()\n\n")}

        self.plotly_plotter = PlotlyPlotter()

        self.plotly_globals = {}

        self.css = {}
        self.js_top = {}
        self.js_bottom = {}
        self.js_onload = {}

    def url_for_figure(self, s):
        """
        Override it to use flask.url_for
        :param s:
        :return:
        """
        return "/fig/" + s

    def make_python_fig(self, code: str, exts=('pdf', 'svg'), tight_layout=True):
        if isinstance(exts, str):
            exts = (exts, )
        hashsum = hashlib.md5(code.encode('utf8')).hexdigest()
        prefix = hashsum[:2]
        path = os.path.join(self.figures_dir, prefix, hashsum)
        needfigure = False
        for ext in exts:
            if not os.path.isfile(os.path.join(path, self.default_figname + "." + ext)):
                needfigure = True
                break

        if needfigure:
            make_sure_path_exists(path)
            loc = {}
            gl = self.pythonfigure_globals
            plt.close()
            exec(code, gl, loc)
            if tight_layout:
                plt.tight_layout()
            for ext in exts:
                plt.savefig(os.path.join(path, self.default_figname + "." + ext))
        return os.path.join(prefix, hashsum)

    def make_plotly_fig(self, code):
        global plotly
        if plotly is None:
            import plotly
        loc = {}
        self.plotly_globals.update({'plot': self.plotly_plotter.plot, 'go': plotly.graph_objs, 'plotly': plotly})

        gl = self.plotly_globals
        exec(code, gl, loc)
        self.js_top['plotly'] = "<script src='https://cdn.plot.ly/plotly-latest.min.js'></script>"
        return self.plotly_plotter.get_data()

    def uses_tags(self):
        members = inspect.getmembers(self, predicate=inspect.ismethod)
        handles = [member for member in members if member[0].startswith("handle_") or member[0] == 'preprocess']
        alltags = set([])
        for handle in handles:
            if handle[0].startswith("handle_"):
                alltags.add(handle[0][len("handle_"):])
            doc = handle[1].__doc__
            if not doc:
                continue
            for line in doc.splitlines():
                m = re.search(r"Uses tags:(.+)", line)
                if m:
                    tags = m.group(1).split(",")
                    tags = [tag.strip() for tag in tags]
                    alltags.update(tags)
        alltags.update(self.enumerateable_envs.keys())
        return alltags

    def localize(self, s):
        return self.localnames.get(s, s)

    def handle(self, tag):
        name = tag.name
        default_handler = 'handle_'+name
        if re.match(r"h\d$",name):
            return self.handle_h(tag)
        elif name in self.enumerateable_envs:
            return self.handle_enumerateable(tag)
        elif hasattr(self, default_handler):
            return getattr(self, default_handler)(tag)
        else:
            return ""

    def blanks_to_pars(self, s, keep_end_pars=True):
        if not keep_end_pars:
            s = s.rstrip()

        return re.sub(r"\n\s*\n", "\n</p>\n<p>\n", s)


    def label2id(self, label):
        return "label_" + mk_safe_css_ident(label.strip())

    def format(self, content, blanks_to_pars=True, keep_end_pars=True) -> str:
        """
        :param content: could be QqTag or any iterable of QqTags
        :param blanks_to_pars: use blanks_to_pars (True or False)
        :return: str: text of tag
        """
        if content is None:
            return ""

        out = []

        for child in content:
            if isinstance(child, str):
                if blanks_to_pars:
                    out.append(self.blanks_to_pars(child, keep_end_pars))
                else:
                    out.append(child)
            else:
                out.append(self.handle(child))
        return "".join(out)

    def handle_h(self, tag: QqTag) -> str:
        """
        Uses tags: h1, h2, h3, h4, label, number

        Example:

            \h1 This is first header

            \h2 This is the second header \label{sec:second}

        :param tag:
        :return:
        """
        doc, html, text = Doc().tagtext()
        with html(tag.name):
            doc.attr(id=self.tag_id(tag))
            if tag.find("number"):
                with html("span", klass="section__number"):
                    with html("a", href="#"+self.tag_id(tag), klass="section__number"):
                        text(tag._number.value)
            text(self.format(tag, blanks_to_pars=False))
        ret = doc.getvalue()
        if tag.next() and isinstance(tag.next(), str):
            ret += "<p>"
        return doc.getvalue()


    def handle_eq(self, tag: QqTag) -> str:
        """
        eq tag corresponds to \[ \] or $$ $$ display formula without number.

        Example:

        \eq
            x^2 + y^2 = z^2

        :param tag:
        :return:
        """
        doc, html, text = Doc().tagtext()
        with html("div", klass="latex_eq"):
            text("\\[\n")
            text(self.format(tag, blanks_to_pars=False))
            text("\\]\n")
        return doc.getvalue()

    def handle_equation(self, tag: QqTag) -> str:
        """
        Uses tags: equation, number, label

        Example:

        \equation \label eq:first
            x^2 + y^2 = z^2

        :param tag:
        :return:
        """
        doc, html, text = Doc().tagtext()
        with html("div", klass="latex_equation"):
            text("\\[\n")
            text("\\begin{equation}\n")
            if tag.find('number'):
                text("\\tag{{{}}}\n".format(tag._number.value))
            if tag.find('label'):
                doc.attr(id=self.label2id(tag._label.value))
            text(self.format(tag, blanks_to_pars=False))
            text("\\end{equation}\n")
            text("\\]\n")
        return doc.getvalue()

    def handle_align(self, tag: QqTag) -> str:
        """
        Uses tags: align, number, label, item

        Example:
            \align
                \item c^2 &= a^2 + b^2 \label eq:one
                \item c &= \sqrt{a^2 + b^2} \label eq:two

        :param tag:
        :return:
        """

        template = Template(
            r"""\[
\begin{align}
<% items = tag("item") %>
% if items:
% for i, item in enumerate(items):
${formatter.format(item, blanks_to_pars=False)}
% if item.exists("number"):
\tag{${item._number.value}}
% endif
% if i != len(items):
\\\

% endif
% endfor
% endif
\end{align}
\]
"""
        )
        return template.render(formatter=self, tag=tag)


    def handle_ref(self, tag: QqTag):
        """
        Examples:

            See Theorem \ref{thm:existence}

        Other way:

            See \ref[Theorem|thm:existence]

        In this case word ``Theorem'' will be part of a reference: e.g. in HTML it will look like

            See <a href="#label_thm:existence">Theorem 1</a>

        If you want to omit number, just use \nonumber tag like so:

            See \ref[Theorem\nonumber|thm:existence]

        This will produce HTML like
            See <a href="#label_thm:existence">Theorem</a>


        Uses tags: ref, nonumber

        :param tag:
        :return:
        """
        doc, html, text = Doc().tagtext()
        if tag.is_simple:
            prefix = None
            label = tag.value
        else:
            prefix, label = tag.children_values(not_simple='keep')

        number = self.label2number.get(label, "???")
        target = self.label2tag[label]
        href = ""
        if self.mode == 'bychapters':
            if 'snippet' not in [t.name for t in tag.ancestor_path()]:
                # check that we're not inside snippet now
                fromindex = self.tag2chapter(tag)
            else:
                fromindex = None
            href = self.url_for_chapter(self.tag2chapter(target),
                                        fromindex=fromindex)

        eqref = (target.name in self.formulaenvs or
                 target.name == 'item' and
                 target.parent.name in self.formulaenvs)

        if eqref:
            href += "#mjx-eqn-" + str(number)
        else:
            href += "#"+self.label2id(label)

        with html("span", klass="ref"):
            with html("a", klass="a-ref", href=href,
                      title=self.label2title.get(label, "")):
                if prefix:
                    doc.asis(self.format(prefix, blanks_to_pars=False))
                if eqref and hasattr(self, 'url_for_eq_snippet'):
                    doc.attr(('data-url', self.url_for_eq_snippet(number)))
                if not tag.exists("nonumber"):
                    if prefix:
                        doc.asis(" ")
                    if eqref:
                        text("(" + number + ")")
                    else:
                        text(number)
        return doc.getvalue()

    def handle_snref(self, tag: QqTag) -> str:
        """
        Makes snippet ref.

        Example:

            Consider \snref[Initial Value Problem|sn:IVP].

        Here sn:IVP -- label of snippet.

        If no separator present, fuzzy search will be performed over flabels

        Example:

        \snippet \label sn:IVP \flabel Initial Value Problem
            Initial Value Problem is a problem with initial value

        Consider \snref[initial value problem].


        :param tag:
        :return:
        """

        doc, html, text = Doc().tagtext()
        if tag.exists("_item"):
            title, label = tag.children_values(not_simple='keep')
            # TODO: testme
        else:
            title = tag.value.replace("\n", " ")
            target = self.find_tag_by_flabel(title)
            label = target._label.value

        data_url = self.url_for_snippet(label)
        with html("a", ('data-url', data_url), klass="snippet-ref"):
            doc.asis(self.format(title, blanks_to_pars=True))
        return doc.getvalue()

    def url_for_snippet(self, label):
        """
        Returns url for snippet by label.

        Override this method to use Flask's url_for

        :param label:
        :return:
        """
        return "/snippet/"+label

    def handle_eqref(self, tag: QqTag) -> str:
        """
        Alias to handle_ref

        Refs to formulas are ALWAYS in parenthesis

        :param tag:
        :return:
        """
        return self.handle_ref(tag)

    def handle_enumerateable(self, tag):
        """
        Uses tags: label, number, name
        Add tags used manually from enumerateable_envs

        :param tag:
        :return:
        """
        doc, html, text = Doc().tagtext()
        name = tag.name
        env_localname = self.localize(self.enumerateable_envs[name])
        with html("div", klass="env env__" + name):
            if tag.find("label"):
                doc.attr(id=self.label2id(tag._label.value))

            number = tag.get("number", "")
            with html("span", klass="env-title env-title__" + name):
                if tag.find("label"):
                    with html("a", klass="env-title env-title__" + name, href="#" + self.label2id(tag._label.value)):
                        text(join_nonempty(env_localname, number) + ".")
                else:
                    text(join_nonempty(env_localname, number) + ".")

            doc.asis(" " + self.format(tag, blanks_to_pars= True))
        return "<p>"+doc.getvalue()+"</p>\n<p>"

    def handle_proof(self, tag: QqTag) -> str:
        """
        Uses tags: proof, label, outline, of

        Examples:

            \proof
                Here is the proof

            \proof \of theorem \ref{thm:1}
                Now we pass to proof of theorem \ref{thm:1}

        :param tag:
        :return: HTML of proof
        """
        doc, html, text = Doc().tagtext()
        with html("div", klass="env env__proof"):
            if tag.find("label"):
                doc.attr(id=self.label2id(tag._label.value))
            with html("span", klass="env-title env-title__proof"):
                if tag.exists("outline"):
                    proofline = 'Proof outline'
                else:
                    proofline = 'Proof'
                doc.asis(join_nonempty(self.localize(proofline),
                                       self.format(tag.find("of"), blanks_to_pars=False)).rstrip()+".")
            doc.asis(rstrip_p(" " + self.format(tag, blanks_to_pars=True)))
            doc.asis("<span class='end-of-proof'>&#8718;</span>")
        return doc.getvalue()+"\n<p>"

    def handle_paragraph(self, tag: QqTag):
        """
        :param tag:
        :return:
        """
        doc, html, text = Doc().tagtext()
        with html("span", klass="paragraph"):
            doc.asis(self.format(tag, blanks_to_pars=False).strip() + ".")
        return "<p>" + doc.getvalue()+" "

    def handle_list(self, tag: QqTag, type):
        doc, html, text = Doc().tagtext()
        with html(type):
            for item in tag("item"):
                with html("li"):
                    doc.asis(self.format(item))
        return doc.getvalue()
    def handle_enumerate(self, tag: QqTag):
        """
        Uses tags: item
        :param tag:
        :return:
        """
        return self.handle_list(tag, "ol")

    def handle_itemize(self, tag: QqTag):
        """
        Uses tags: item
        :param tag:
        :return:
        """
        return self.handle_list(tag, "ul")

    def handle_figure(self, tag: QqTag) -> str:
        """
        Currently, only python-generated figures and plotly figures are supported.

        Example:

        \figure \label fig:figure
            \pythonfigure
                plt.plot([1, 2, 3], [1, 4, 9])
            \caption
                Some figure

        Uses tags: figure, label, caption, number, showcode, collapsed

        :param tag: QqTag
        :return: HTML of figure
        """
        doc, html, text = Doc().tagtext()
        subtags = ['pythonfigure', 'plotly', 'rawhtml']
        langs = {'pythonfigure': 'python', 'plotly': 'python', 'rawhtml': 'html'}
        with html("div", klass="figure"):
            if tag.find("label"):
                doc.attr(id=self.label2id(tag._label.value))
                label = tag._label.value
            else:
                label = None
            for child in tag:
                if isinstance(child, QqTag):
                    if child.name in subtags:
                        if tag.exists("showcode"):
                            doc.asis(self.showcode(child, collapsed=tag.exists("collapsed"),
                                                   lang = langs.get(child.name)))
                        doc.asis(self.handle(child))
                    elif child.name == 'caption':
                        with html("div", klass="figure_caption"):
                            if label is not None:
                                with html("a", klass="figure_caption_anchor", href="#" + self.label2id(label)):
                                    text(join_nonempty(self.localize("Fig."), tag.get("number")))
                                text(": ")
                            else:
                                text(join_nonempty(self.localize("Fig."), tag.get("number"))+": ")
                            doc.asis(self.format(child, blanks_to_pars=True))
        return doc.getvalue()

    def handle_pythonfigure(self, tag: QqTag) -> str:
        """
        Uses tags: pythonfigure, style

        :param tag:
        :return:
        """

        path = self.make_python_fig(tag.text_content, exts=("svg"))
        doc, html, text = Doc().tagtext()
        with html("img", klass="figure img-responsive",
                  src=self.url_for_figure(path + "/" + self.default_figname + ".svg")):
            if tag.exists("style"):
                doc.attr(style=tag._style.value)
        return doc.getvalue()

    def handle_plotly(self, tag: QqTag) -> str:
        return "".join(self.make_plotly_fig(tag.text_content))

    def showcode(self, tag: QqTag, collapsed = False, lang = None) -> str:
        """
        <button class="source toggle btn btn-xs btn-primary">
<span class="glyphicon glyphicon-chevron-up"></span>
</button>

        :param tag:
        :return:
        """

        self.css['highlightjs'] = (
            '<link rel="stylesheet" '
            'href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.2.0/styles/default.min.css">\n'
            '<style type="text/css">\n'
            '.hljs {background: inherit;}\n'
            '</style>\n'
        )
        self.js_top['highlightjs'] = (
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.2.0/highlight.min.js"></script>\n'
            '<script>hljs.initHighlightingOnLoad();</script>'
        )
        self.js_onload['highlightjs'] = """
        function toggle_block(obj, show) {
          var span = obj.find('span');
          if(show === true){
            span.removeClass('glyphicon-chevron-up').addClass('glyphicon-chevron-down');
            obj.next('pre').slideDown();
          }
          else {
            span.removeClass('glyphicon-chevron-down').addClass('glyphicon-chevron-up');
            obj.next('pre').slideUp();
          }
        }

        /* onclick toggle next code block */
        $('.toggle').click(function() {
          var span = $(this).find('span');
          toggle_block($(this), !span.hasClass('glyphicon-chevron-down'));
          return false
        })
        """
        button = """
        <button class="source toggle btn btn-xs btn-primary">
        <span class="glyphicon glyphicon-chevron-up"></span>
        </button>
        """

        if not collapsed:
            button = button.replace("glyphicon-chevron-up", "glyphicon-chevron-down")

        doc, html, text = Doc().tagtext()
        with html("pre"):
            if collapsed:
                doc.attr(style="display:none")
            with html("code"):
                if lang:
                    doc.attr(klass="lang-" + lang)

                doc.asis(self.code_prefixes.get(tag.name, "# "+tag.name))
                # add a prefix if exists

                doc.asis(tag.text_content)

        return "<div style='text-align: left'>" + button + doc.getvalue() + "</div>"


    def handle_snippet(self, tag: QqTag) -> str:
        """
        Uses tags: hidden, backref, label

        :param tag:
        :return:
        """
        anchor = ""
        if not tag.exists("backref") and tag.exists("label"):
            anchor = "<span id='{}'></span>".format(self.label2id(tag._label.value))
        if tag.exists("hidden"):
            return anchor
        return anchor + self.format(tag, blanks_to_pars=True)

    def handle_hide(self, tag: QqTag) -> str:
        """
        :param tag:
        :return:
        """
        return ""

    def handle_em(self, tag: QqTag) -> str:
        """
        Example:
            Let us define \em{differential equation}.

        :param tag:
        :return:
        """
        return "<em>" + self.format(tag) + "</em>"

    def handle_emph(self, tag: QqTag) -> str:
        """
        Alias for em
        :param tag:
        :return:
        """
        return self.handle_em(tag)



    def get_counter_for_tag(self, tag: QqTag) -> Counter:
        name = tag.name
        counters = self.counters
        while True:
            if tag.exists('nonumber'):
                return None
            current = counters.get(name)
            if current is None:
                return None
            if isinstance(current, Counter):
                return current
            if isinstance(current, dict):
                counters = current
                tag = tag.parent
                name = tag.name
                continue
            return None

    def preprocess(self, root: QqTag):
        """
        Uses tags: number, label, nonumber, flabel

        :return:
        """
        for tag in root:
            if isinstance(tag, QqTag):
                name = tag.name
                if (name in self.counters or name in self.enumerateable_envs) and not (tag.find('number') or
                                                                                           tag.exists('nonumber')):
                    counter = self.get_counter_for_tag(tag)
                    if counter is not None:
                        counter.increase()
                        tag.append_child(QqTag({'number': str(counter)}))
                        if tag.find('label'):
                            label = tag._label.value
                            self.label2number[label] = str(counter)
                            # self.label2title[label] = tag.text_content
                if tag.find('label') and tag.find('number'):
                    self.label2number[tag._label.value] = tag._number.value
                if tag.find('label'):
                    self.label2tag[tag._label.value] = tag
                if tag.find('flabel'):
                    self.flabel2tag[tag._flabel.value.lower()] = tag
                self.preprocess(tag)

    def find_tag_by_flabel(self, s):
        flabel = process.extractOne(s.lower(), self.flabel2tag.keys())[0]
        return self.flabel2tag.get(flabel)

    def mk_chapters(self):
        curchapter = Chapter(QqTag("_zero_chapter"),  [])
        self.chapters = []
        for tag in self.root:
            if isinstance(tag, QqTag) and tag.name == 'h1':
                self.add_chapter(curchapter)
                curchapter = Chapter(tag, [])
            curchapter.content.append(tag)
        self.add_chapter(curchapter)

    def tag2chapter(self, tag) -> int:
        """
        Returns the number of chapter to which tag belongs.

        Chapters are separated by `h1` tag. Chapter before the first `h1` tag has number zero.

        :param tag:
        :return:
        """

        eva = tag.get_eva()
        headers = self.root("h1")
        i = 0
        for i, header in enumerate(headers, 1):
            if eva.index < header.index:
                return i - 1
        return i

    def url_for_chapter(self, index=None, label=None, fromindex=None) -> str:
        """
        Returns url for chapter. Either index or label of the target chapter have to be provided.
        Optionally, fromindex can be provided. In this case function will return empty string if
        target chapter coincides with current one.

        You can inherit from QqHTMLFormatter and override url_for_chapter_by_index and url_for_chapter_by_label too
        use e.g. Flask's url_for.
        """
        assert index is not None or label is not None
        if index is None:
            index = self.label2chapter[label]
        if fromindex is not None and fromindex == index:
            # we are already on the right page
            return ""
        if label is None:
            label = self.chapters[index].header.find("label")
        if not label:
            return self.url_for_chapter_by_index(index)
        return self.url_for_chapter_by_label(label.value)

    def url_for_chapter_by_index(self, index):
        return "/chapter/index/" + urllib.parse.quote(str(index))

    def url_for_chapter_by_label(self, label):
        return "/chapter/label/" + urllib.parse.quote(label)


    def add_chapter(self, chapter):
        if chapter.header.find("label"):
            self.label2chapter[chapter.header._label.value] = len(self.chapters)
        self.chapters.append(chapter)

    def do_format(self):
        self.preprocess(self.root)
        return self.format(self.root, blanks_to_pars=True)

    def tag_id(self, tag) -> str:
        """
        Returns id of tag:
        - If it has label, it is label-based
        - If it does not have label, but have number, it is number-based
        :param tag:
        :return: str id
        """
        if tag.find("label"):
            return self.label2id(tag._label.value)
        elif tag.find("number"):
            return self.label2id(tag.name+"_number_"+str(tag._number.value))
        else:
            return ""

    def mk_toc(self, maxlevel=2, chapter = None) -> str:
        """
        Makes TOC (Table Of Contents)

        :param maxlevel: maximum heading level to include to TOC (default: 2)
        :param chapter: if None, we assume to have whole document on the same page and TOC contains only local links.
        If present, it is equal to index of current chapter
        :return: str with HTML content of TOC
        """
        doc, html, text = Doc().tagtext()
        curlevel = 1

        curchapter = 0
        # chapter before first h1 has index 0

        with html("ul", klass="nav"):
            for child in self.root:
                chunk = []
                if isinstance(child, QqTag):
                    m = re.match(r'h(\d)', child.name)
                    if m:
                        hlevel = int(m.group(1))

                        # h1 header marks new chapter, so increase curchapter counter
                        if hlevel == 1:
                            curchapter += 1

                        if hlevel > maxlevel:
                            continue
                        while hlevel > curlevel:
                            chunk.append("<li><ul class='nav'>\n")
                            curlevel += 1
                        while hlevel < curlevel:
                            chunk.append("</ul></li>\n")
                            curlevel -= 1

                        targetpage = self.url_for_chapter(index=curchapter, fromindex=chapter)

                        item_doc, item_html, item_text = Doc().tagtext()
                        with item_html("li", klass = "toc_item toc_item_level_%i" % curlevel):
                            with item_html("a", href=targetpage+"#"+self.tag_id(child)):
                                item_text(self.format(child, blanks_to_pars=False))
                        chunk.append(item_doc.getvalue())
                        doc.asis("".join(chunk))
        return doc.getvalue()

    def tag_hash_id(self, tag):
        """
        Returns autogenerated tag id based on tag's contents.
        It's first 5 characters of MD5-hashsum of tag's content
        :return:
        """
        return hashlib.md5(repr(tag.as_list()).encode('utf-8')).hexdigest()[:5]

    def handle_quiz(self, tag: QqTag):
        """
        Uses tags: choice, correct, comment

        Example:

        \question
        Do you like qqmbr?
        \quiz
            \choice
                No.
                \comment You didn't even try!
            \choice \correct
                Yes, i like it very much!
                \comment And so do I!

        :param tag:
        :return:
        """
        if not tag.exists('md5id'):
            tag.append_child(QqTag('md5id', [self.tag_hash_id(tag)]))
        template = Template(filename=os.path.join(self.templates_dir,
                                                  "quiz.html"))
        return template.render(formatter=self, tag=tag)

    def handle_rawhtml(self, tag: QqTag):
        return tag.text_content

    ### TODO: Add handle_href
    # def handle_href(self, tag: QqTag):

