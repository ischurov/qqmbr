# (c) Ilya V. Schurov, 2016
# Available under MIT license (see LICENSE file in the root folder)

from indentml.parser import QqTag
from yattag import Doc
import re
import inspect
import hashlib
import os
import urllib.parse
from mako.template import Template
from fuzzywuzzy import process
from html import escape as html_escape
from typing import Optional, List
from typing import (
    NamedTuple,
    TypeVar,
    Sequence,
    Tuple,
    Dict,
    Iterator,
    Any,
)
from textwrap import indent, dedent
import contextlib
import sys
from io import StringIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from celluloid import Camera


def mk_safe_css_ident(s):
    # see http://stackoverflow.com/a/449000/3025981 for details
    s = re.sub(r"[^a-zA-Z\d_-]", "_", s)
    if re.match(r"([^a-zA-Z]+)", s):
        m = re.match(r"([^a-zA-Z]+)", s)
        first = m.group(1)
        s = s[len(first) :] + "__" + first
    return s


# FROM http://stackoverflow.com/a/14364249/3025981
def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.isdir(path):
            raise


# END FROM

# FROM: http://stackoverflow.com/a/3906390/3025981
@contextlib.contextmanager
def stdout_io(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old


# END FROM


T = TypeVar("T")


# BASED ON: https://stackoverflow.com/a/15358005/3025981
def split_by_predicate(
    seq: Sequence[T], predicate, zero_delim: Optional[T] = None
) -> Iterator[Sequence[T]]:
    """
    Splits a sequence by delimeters that satisfy predicate,
    keeping the delimeters

    split_by_predicate([0, "One", 1, 2, 3,
                    "Two", 4, 5, 6, 7, "Three", "Four"],
                    predicate=lambda x: isinstance(x, str),
                    zero_delim="Nothing")

    [["Nothing", 0], ["One", 1, 2, 3], ["Two", 4, 5, 6, 7],
    ["Three"], ["Four"]]

    :param seq: sequence to proceed
    :param predicate: checks whether element is delimeter
    :param zero_delim: pseudo-delimter prepended to the sequence
    :return: sequence of sequences
    """
    g = [zero_delim]
    for el in seq:
        if predicate(el):
            yield g
            g = []
        g.append(el)
    yield g


# END BASED


class Counter(object):
    """
    Very simple class that support latex-style counters with subcounters.
    For example, if new section begins, the enumeration of subsections
    resets.
    If `showparents` option is set, str(counter) contains numbers of all
    its parents
    That's all.
    """

    def __init__(self, showparents=True):
        self.value = 0
        self.children: List["Counter"] = []
        self.parent: Counter = None
        self.showparents = showparents

    def reset(self):
        self.value = 0
        for child in self.children:
            child.reset()

    def increase(self):
        self.value += 1
        for child in self.children:
            child.reset()

    def spawn_child(self) -> "Counter":
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


Chapter = NamedTuple("Chapter", (("heading", QqTag), ("content", List)))


class TOCItem(object):
    def __init__(
        self, tag: QqTag = None, parent: "TOCItem" = None, level=0
    ) -> None:
        self.tag = tag
        self.children: List["TOCItem"] = []
        self.parent = parent
        self.level = level

    def __str__(self):
        return "{}: {}\n".format(
            self.tag and self.tag.name, self.tag and self.tag.text_content
        ) + indent("".join(str(child) for child in self.children), " " * 4)

    def as_tuple(self):
        return (
            self.tag and self.tag.name,
            [child.as_tuple() for child in self.children],
        )

    def spawn_child(self, tag: QqTag = None):
        new = TOCItem(tag, parent=self, level=self.level + 1)
        self.children.append(new)
        return new


class FormattedTOCItem(object):
    def __init__(
        self,
        tag: QqTag = None,
        parent: "FormattedTOCItem" = None,
        string: str = None,
        href: str = None,
        iscurchapter=False,
    ) -> None:
        self.tag = tag
        self.parent = parent
        self.children: List["FormattedTOCItem"] = []
        self.string = string
        self.href = href

        self.iscurchapter = iscurchapter
        # item is a chapter that is currently shown

    def append_child(self, child: "FormattedTOCItem"):
        child.parent = self
        self.children.append(child)


plotly = None


class PlotlyPlotter(object):
    _first = True

    def __init__(self):
        self.buffer = []

    def plot(self, figure_or_data) -> None:
        self.buffer.append(
            plotly.offline.plot(
                figure_or_data,
                show_link=False,
                validate=True,
                output_type="div",
                include_plotlyjs=False,
            )
        )
        PlotlyPlotter._first = False

    def get_data(self) -> str:
        ret = "".join(self.buffer)
        self.buffer.clear()
        return ret


def rstrip_p(s: str) -> str:
    return re.sub(r"(\s*</?p>\s*)+$", "", s)


def spawn_or_create_counter(parent: Optional[Counter]):
    if parent is not None:
        return parent.spawn_child()
    else:
        return Counter()


def process_only(tag: QqTag) -> Tuple[QqTag, QqTag]:
    long_tag = QqTag(tag.name, adopt=True)
    splitted_tag = QqTag(tag.name, adopt=True)
    for child in tag:
        if isinstance(child, str) or child.name not in [
            "splonly",
            "longonly",
        ]:
            long_tag.append_child(child)
            splitted_tag.append_child(child)
            continue
        if child.name == "splonly":
            for grandchild in child:
                splitted_tag.append_child(grandchild)
        if child.name == "longonly":
            for grandchild in child:
                long_tag.append_child(grandchild)

    return long_tag, splitted_tag


def extract_splitted_items(tag: QqTag) -> Tuple[QqTag, QqTag]:
    curitem = None
    long_tag = QqTag(tag.name, adopt=True)
    splitted_tag = QqTag(tag.name, adopt=True)
    for child in tag.children_tags():
        long_child, splitted_child = process_only(child)
        if child.name == "item":
            long_tag.append_child(long_child)
            splitted_tag.append_child(splitted_child)
            curitem = long_tag[-1]
        elif child.name == "splitem":
            splitted_tag.append_child(
                QqTag("item", splitted_child, adopt=True)
            )
            for grandchild in child:
                curitem.append_child(grandchild)
    return long_tag, splitted_tag


class QqHTMLFormatter(object):
    def __init__(
        self,
        root: QqTag = QqTag("_root"),
        with_chapters=True,
        eq_preview_by_labels=False,
    ) -> None:

        self.templates_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "templates"
        )

        self.with_chapters = with_chapters
        self.eq_preview_by_labels = eq_preview_by_labels

        self.label_to_number: Dict[str, str] = {}
        self.label_to_title: Dict[str, str] = {}
        self.label_to_tag: Dict[str, QqTag] = {}
        self.label_to_chapter: Dict[str, int] = {}
        self.flabel_to_tag: Dict[str, QqTag] = {}
        self.root: QqTag = root
        self.counters = {}
        self.chapters: List[Chapter] = []
        self.heading_to_level = {
            "chapter": 1,
            "section": 2,
            "subsection": 3,
            "subsubsection": 4,
        }

        self.mode = "wholedoc"
        #: how to render the doc? the following options are available:
        #: - 'wholedoc' - the whole document on one page
        #: - 'bychapters' - every chapter on its own page

        chapters_counter = None
        if with_chapters:
            chapters_counter = Counter()
            self.counters["chapter"] = chapters_counter

        self.counters["section"] = spawn_or_create_counter(
            chapters_counter
        )

        self.counters["subsection"] = self.counters[
            "section"
        ].spawn_child()
        self.counters["subsubsection"] = self.counters[
            "subsection"
        ].spawn_child()

        self.counters["equation"] = spawn_or_create_counter(
            chapters_counter
        )
        self.counters["equation"].showparents = True

        self.counters["item"] = {
            "align": self.counters["equation"],
            "gather": self.counters["equation"],
            "multline": self.counters["equation"],
        }

        self.counters["figure"] = spawn_or_create_counter(chapters_counter)

        self.enumerateable_envs = {
            name: name.capitalize()
            for name in [
                "remark",
                "theorem",
                "example",
                "exercise",
                "definition",
                "quasidefinition",
                "proposition",
                "lemma",
                "question",
                "corollary",
            ]
        }

        self.metatags = {
            "meta",
            "author",
            "affiliation",
            "link",
            "license",
            "title",
            "url",
            "lang",
            "role",
            "codepreamble",
            "preamble",
        }

        # You can make self.localnames = {} to use
        # plain English localization

        self.localizations = {
            "ru": {
                "Remark": "Замечание",
                "Theorem": "Теорема",
                "Example": "Пример",
                "Exercise": "Упражнение",
                "Definition": "Определение",
                "Proposition": "Утверждение",
                "Lemma": "Лемма",
                "Proof": "Доказательство",
                "Proof outline": "Набросок доказательства",
                "Figure": "Рисунок",
                "Fig.": "Рис.",
                "Question": "Вопрос",
                "Corollary": "Следствие",
                "Quasidefinition": "Как бы определение",
            }
        }

        self.localnames: Dict[str, str] = None

        self.formulaenvs = {"eq", "equation", "align", "gather"}

        for env in self.enumerateable_envs:
            self.counters[env] = spawn_or_create_counter(chapters_counter)
            self.counters[env].showparents = False

        self.figures_dir = None

        self.default_figname = "fig"

        plt.rcParams["figure.figsize"] = (6, 4)
        plt.rcParams["animation.frame_format"] = "svg"

        self.pythonfigure_globals = {"plt": plt, "Camera": Camera}
        self.code_prefixes = dict(
            pythonfigure="import matplotlib.pyplot as plt\n",
            plotly=(
                "import plotly\n"
                "import plotly.graph_objs as go\n"
                "from plotly.offline import iplot "
                "as plot\n"
                "from plotly.offline import "
                "init_notebook_mode\n\n"
                "init_notebook_mode()\n\n"
            ),
            rawhtml="",
            pythoncode="",
        )

        self.plotly_plotter = PlotlyPlotter()

        self.plotly_globals: Dict[str, Any] = {}

        self.python_globals: Dict[str, Any] = {}

        self.css: Dict[str, str] = {}
        self.js_top: Dict[str, str] = {}
        self.js_bottom: Dict[str, str] = {}
        self.js_onload: Dict[str, str] = {}

        self.safe_tags = (
            set(self.enumerateable_envs)
            | set(self.formulaenvs)
            | {
                "item",
                "figure",
                "label",
                "number",
                "ref",
                "nonumber",
                "snref",
                "snippet",
                "flabel",
                "name",
                "proof",
                "outline",
                "of",
                "caption",
                "showcode",
                "collapsed",
                "hidden",
                "backref",
                "label",
                "em",
                "emph",
                "tt",
                "quiz",
                "choice",
                "correct",
                "comment",
            }
            | set(self.heading_to_level)
            | self.metatags
        )

    def url_for_figure(self, s: str):
        """
        Override it to use flask.url_for
        :param s:
        :return:
        """
        return "/fig/" + s

    def url_for_img(self, s: str):
        return "/img/" + s

    def make_python_fig(
        self,
        code: str,
        exts: Tuple[str, ...] = ("pdf", "svg"),
        tight_layout=True,
        video=False,
    ) -> str:
        hashsum = hashlib.md5(code.encode("utf8")).hexdigest()
        prefix = hashsum[:2]
        path = os.path.join(self.figures_dir, prefix, hashsum)
        needfigure = False
        for ext in exts:
            if not os.path.isfile(
                os.path.join(path, self.default_figname + "." + ext)
            ):
                needfigure = True
                break

        if needfigure:
            make_sure_path_exists(path)
            gl = self.pythonfigure_globals
            plt.close()
            exec(code, gl)
            if video:
                animation = gl["animation"]
                for ext in exts:
                    animation.save(
                        os.path.join(
                            path, self.default_figname + "." + ext
                        )
                    )

            else:
                if tight_layout:
                    plt.tight_layout()
                for ext in exts:
                    plt.savefig(
                        os.path.join(
                            path, self.default_figname + "." + ext
                        )
                    )

        return os.path.join(prefix, hashsum)

    def make_python_jsanimate(self, code: str):
        gl = self.pythonfigure_globals
        plt.close()
        exec(code, gl)
        animation = gl["animation"]
        return animation.to_jshtml(default_mode="once")

    def make_plotly_fig(self, code: str) -> str:
        global plotly
        if plotly is None:
            import plotly
        loc: Dict[str, Any] = {}
        self.plotly_globals.update(
            {
                "plot": self.plotly_plotter.plot,
                "go": plotly.graph_objs,
                "plotly": plotly,
            }
        )

        gl = self.plotly_globals
        exec(code, gl, loc)
        self.js_top["plotly"] = (
            "<script src='https://cdn.plot.ly/plotly-"
            "latest.min.js'></script>"
        )
        return self.plotly_plotter.get_data()

    def uses_tags(self) -> set:
        members = inspect.getmembers(self, predicate=inspect.ismethod)
        handles = [
            member
            for member in members
            if (
                member[0].startswith("handle_")
                or member[0] == "make_numbers"
            )
        ]
        alltags = set([])
        for handle in handles:
            if handle[0].startswith("handle_"):
                alltags.add(handle[0][len("handle_") :])
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
        alltags.update(self.metatags)
        return alltags

    def localize(self, s: str) -> str:
        if not self.localnames:
            self.localnames = self.localizations.get(
                self.root.meta_.get("lang"), {}
            )
        return self.localnames.get(s, s)

    def handle(self, tag: QqTag) -> str:
        name = tag.name
        default_handler = "handle_" + name
        if name in self.heading_to_level:
            return self.handle_heading(tag)
        elif name in self.enumerateable_envs:
            return self.handle_enumerateable(tag)
        elif hasattr(self, default_handler):
            return getattr(self, default_handler)(tag)
        else:
            return ""

    @staticmethod
    def blanks_to_pars(s: str, keep_end_pars=True) -> str:
        if not keep_end_pars:
            s = s.rstrip()

        return re.sub(r"\n\s*\n", "\n</p>\n<p>\n", s)

    @staticmethod
    def label2id(label: str) -> str:
        return "label_" + mk_safe_css_ident(label.strip())

    def format(
        self,
        content: Optional[QqTag],
        blanks_to_pars=True,
        keep_end_pars=True,
    ) -> str:
        """
        :param content: could be QqTag or any iterable of QqTags
        :param blanks_to_pars: use blanks_to_pars (True or False)
        :param keep_end_pars: keep end paragraphs
        :return: str: text of tag
        """
        if content is None:
            return ""

        out = []

        for child in content:
            if isinstance(child, str):
                if blanks_to_pars:
                    out.append(
                        self.blanks_to_pars(
                            html_escape(child, keep_end_pars)
                        )
                    )
                else:
                    out.append(html_escape(child))
            else:
                out.append(self.handle(child))
        return "".join(out)

    def handle_heading(self, tag: QqTag) -> str:
        """
        Uses tags: chapter, section, subsection, subsubsection
        Uses tags: label, number

        Example:

            \chapter This is first heading

            \section This is the second heading \label{sec:second}

        :param tag:
        :return:
        """
        tag_to_hx = {
            "chapter": "h1",
            "section": "h2",
            "subsection": "h3",
            "subsubsection": "h4",
        }

        doc, html, text = Doc().tagtext()
        with html(tag_to_hx[tag.name]):
            doc.attr(id=self.tag_id(tag))
            if tag.find("number"):
                with html("span", klass="section__number"):
                    with html(
                        "a",
                        href="#" + self.tag_id(tag),
                        klass="section__number",
                    ):
                        text(tag.number_.value)
            doc.asis(self.format(tag, blanks_to_pars=False))
        ret = doc.getvalue()
        if tag.next() and isinstance(tag.next(), str):
            ret += "<p>"
        return doc.getvalue()

    def handle_eq(self, tag: QqTag) -> str:
        """
        eq tag corresponds to \[ \] or $$ $$ display formula
        without number.

        Example:

        \eq
            x^2 + y^2 = z^2

        :param tag:
        :return:
        """
        doc, html, text = Doc().tagtext()
        with html("div", klass="latex_eq"):
            text("\\[\n")
            doc.asis(self.format(tag, blanks_to_pars=False))
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
            if tag.find("number"):
                text("\\tag{{{}}}\n".format(tag.number_.value))
            if tag.find("label"):
                doc.attr(id=self.label2id(tag.label_.value))
            doc.asis(self.format(tag, blanks_to_pars=False))
            text("\\end{equation}\n")
            text("\\]\n")
        return doc.getvalue()

    def multieq_template(self, name: str, tag: QqTag) -> str:
        template = Template(
            dedent(
                r"""
                \[
                \begin{${name}}
                <% items = tag("item") %>
                % if items:
                    % for i, item in enumerate(items):
                        ${formatter.format(item, blanks_to_pars=False)}
                        % if item.exists("number"):
                            \tag{${item.number_.value}}
                        % endif
                        % if i != len(items):
                            \\\
                        
                        % endif
                        % endfor
                % endif
                \end{${name}}
                \]
                """
            )
        )
        if tag.exists("splitem"):
            long_tag, splitted_tag = extract_splitted_items(tag)
            print(long_tag, splitted_tag)
            return dedent(
                f"""
                <div class='long-eq'>
                { template.render(formatter=self, tag=long_tag, name=name) }
                </div>
                <div class='splitted-eq'>
                { template.render(formatter=self, 
                                   tag=splitted_tag, 
                                   name=name) }
                </div>
                """
            )
        return template.render(formatter=self, tag=tag, name=name)

    def handle_align(self, tag: QqTag) -> str:
        """
        Uses tags: align, number, label, item, splitem, splonly, longonly

        Example:
            \\align
                \\item c^2 &= a^2 + b^2 \\label eq:one
                \\item c &= \\sqrt{a^2 + b^2} \\label eq:two

        :param tag:
        :return:
        """
        return self.multieq_template(name="align", tag=tag)

    def handle_gather(self, tag: QqTag) -> str:
        """
        Uses tags: gather, number, label, item, splitem, splonly, longonly

        Example:
            \\gather
                \\item c^2 &= a^2 + b^2 \\label eq:one
                \\item c &= \\sqrt{a^2 + b^2} \\label eq:two

        :param tag:
        :return:
        """
        return self.multieq_template(name="gather", tag=tag)

    def handle_multline(self, tag: QqTag) -> str:
        """
        Uses tags: multline, number, label, item, splitem, splonly, longonly

        Example:
            \\multline
                \\item c^2 &= a^2 + b^2 \\label eq:one
                \\item c &= \\sqrt{a^2 + b^2} \\label eq:two

        :param tag:
        :return:
        """
        return self.multieq_template(name="multline", tag=tag)

    def handle_ref(self, tag: QqTag):
        """
        Examples:

            See Theorem \ref{thm:existence}

        Other way:

            See \ref[Theorem|thm:existence]

        In this case word ``Theorem'' will be part of a reference: e.g.
        in HTML it will look like

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
        if len(tag) == 1:
            tag = tag.unitemized()

        if tag.is_simple:
            prefix = None
            label = tag.value
        else:
            if len(tag) != 2:
                raise Exception(
                    "Incorrect number of arguments in "
                    + str(tag)
                    + ": 2 arguments expected"
                )

            prefix, label = tag.children_values(not_simple="keep")

        number = self.label_to_number.get(label, "[" + label + "]")
        target = self.label_to_tag.get(label)

        href = ""
        if self.mode == "bychapters":
            if "snippet" not in [t.name for t in tag.ancestor_path()]:
                # check that we're not inside snippet now
                fromindex = self.tag2chapter(tag)
            else:
                fromindex = None
            href = (
                self.url_for_chapter(
                    self.tag2chapter(target), fromindex=fromindex
                )
                if target
                else ""
            )

        eqref = target and (
            target.name in self.formulaenvs
            or target.name == "item"
            and target.parent.name in self.formulaenvs
        )

        if eqref:
            href += "#mjx-eqn-" + str(number)
        else:
            href += "#" + self.label2id(label)

        with html("span", klass="ref"):
            with html(
                "a",
                klass="a-ref",
                href=href,
                title=self.label_to_title.get(label, ""),
            ):
                if prefix:
                    doc.asis(self.format(prefix, blanks_to_pars=False))
                if eqref:
                    eq_id = label if self.eq_preview_by_labels else number
                    try:
                        doc.attr(
                            ("data-url", self.url_for_eq_snippet(eq_id))
                        )
                    except NotImplementedError:
                        pass
                if not isinstance(prefix, QqTag) or not prefix.exists(
                    "nonumber"
                ):
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

            Consider \snref[Initial Value Problem][sn:IVP].

        Here sn:IVP -- label of snippet.

        If no separator present, fuzzy search will be performed over
        flabels

        Example:

        \snippet \label sn:IVP \flabel Initial Value Problem
            Initial Value Problem is a problem with initial value

        Consider \snref[initial value problem].


        :param tag:
        :return:
        """

        doc, html, text = Doc().tagtext()

        if len(tag) == 1:
            tag = tag.unitemized()
        if tag.is_simple:
            title = tag.value.replace("\n", " ")
            target = self.find_tag_by_flabel(title)
            label = target.label_.value
        else:
            if len(tag) != 2:
                raise Exception(
                    "Incorrect number of arguments in "
                    + str(tag)
                    + (": one or two arguments " "expected")
                )
            title, label = tag.children_values(not_simple="keep")
            # TODO: testme

        data_url = self.url_for_snippet(label)
        with html("a", ("data-url", data_url), klass="snippet-ref"):
            doc.asis(self.format(title, blanks_to_pars=True))
        return doc.getvalue()

    def handle_href(self, tag: QqTag) -> str:
        """
        Example:

            Content from \href[Wikipedia|http://wikipedia.org]

        Uses tags: href

        :param tag: tag to proceed
        :return:
        """
        a, url = tag.children_values(not_simple="keep")
        doc, html, text = Doc().tagtext()
        with html("a", klass="href", href=url.strip()):
            doc.asis(self.format(a.strip(), blanks_to_pars=False))
        return doc.getvalue()

    def url_for_snippet(self, label: str) -> str:
        """
        Returns url for snippet by label.

        Override this method to use Flask's url_for

        :param label:
        :return:
        """
        return "/snippet/" + label

    def url_for_eq_snippet(self, label: str) -> Optional[str]:
        """
        Returns url for equation snippet by label
        Should be implemented in subclass

        :param label:
        :return:
        """
        raise NotImplementedError

    def handle_eqref(self, tag: QqTag) -> str:
        """
        Alias to handle_ref

        Refs to formulas are ALWAYS in parenthesis

        :param tag:
        :return:
        """
        return self.handle_ref(tag)

    def handle_enumerateable(self, tag: QqTag) -> str:
        """
        Uses tags: label, number
        Add tags used manually from enumerateable_envs

        :param tag:
        :return:
        """
        doc, html, text = Doc().tagtext()
        name = tag.name
        env_localname = self.localize(self.enumerateable_envs[name])
        with html("div", klass="env env__" + name):
            if tag.find("label"):
                doc.attr(id=self.label2id(tag.label_.value))

            number = tag.get("number", "")
            with html("span", klass="env-title env-title__" + name):
                if tag.find("label"):
                    with html(
                        "a",
                        klass="env-title env-title__" + name,
                        href="#" + self.label2id(tag.label_.value),
                    ):
                        text(join_nonempty(env_localname, number) + ".")
                else:
                    text(join_nonempty(env_localname, number) + ".")

            doc.asis(" " + self.format(tag, blanks_to_pars=True))
        return "<p>" + doc.getvalue() + "</p>\n<p>"

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
                doc.attr(id=self.label2id(tag.label_.value))
            with html("span", klass="env-title env-title__proof"):
                if tag.exists("outline"):
                    proofline = "Proof outline"
                else:
                    proofline = "Proof"
                doc.asis(
                    join_nonempty(
                        self.localize(proofline),
                        self.format(tag.find("of"), blanks_to_pars=False),
                    ).rstrip()
                    + "."
                )
            doc.asis(rstrip_p(" " + self.format(tag, blanks_to_pars=True)))
            doc.asis("<span class='end-of-proof'>&#8718;</span>")
        return doc.getvalue() + "\n<p>"

    def handle_paragraph(self, tag: QqTag) -> str:
        """
        :param tag:
        :return:
        """
        doc, html, text = Doc().tagtext()
        with html("span", klass="paragraph"):
            doc.asis(self.format(tag, blanks_to_pars=False).strip() + ".")
        # TODO: make paragraphs clickable?
        anchor = ""
        if tag.exists("label"):
            anchor = "<span id='{}'></span>".format(
                self.label2id(tag.label_.value)
            )
        return anchor + "<p>" + doc.getvalue() + " "

    def handle_list(self, tag: QqTag, type_: str) -> str:
        doc, html, text = Doc().tagtext()
        with html(type_):
            for item in tag("item"):
                with html("li"):
                    doc.asis(self.format(item))
        return doc.getvalue()

    def handle_enumerate(self, tag: QqTag) -> str:
        """
        Uses tags: item
        :param tag:
        :return:
        """
        return self.handle_list(tag, "ol")

    def handle_itemize(self, tag: QqTag) -> str:
        """
        Uses tags: item
        :param tag:
        :return:
        """
        return self.handle_list(tag, "ul")

    def handle_figure(self, tag: QqTag) -> str:
        """
        Currently, only python-generated figures, plotly figures and
        <img> tags are supported. Also one can use \rawhtml to embed
        arbitrary HTML code (e.g. use D3.js).

        Example:

        \figure \label fig:figure
            \pythonfigure
                plt.plot([1, 2, 3], [1, 4, 9])
            \caption
                Some figure

        Uses tags: figure, label, caption, number, showcode, collapsed, img
        Uses tags: center, nocenter

        :param tag: QqTag
        :return: HTML of figure
        """
        doc, html, text = Doc().tagtext()
        subtags = [
            "pythonfigure",
            "plotly",
            "rawhtml",
            "img",
            "pythonvideo",
        ]
        langs = {
            "pythonfigure": "python",
            "plotly": "python",
            "rawhtml": "html",
            "pythonvideo": "python",
        }
        with html("div", klass="figure"):
            if tag.find("label"):
                doc.attr(id=self.label2id(tag.label_.value))
                label = tag.label_.value
            else:
                label = None
            for child in tag.children_tags():
                if child.name in subtags:
                    if tag.exists("showcode"):
                        doc.asis(
                            self.showcode(
                                child,
                                collapsed=tag.exists("collapsed"),
                                lang=langs.get(child.name),
                            )
                        )
                    doc.asis(self.handle(child))
                elif child.name == "caption":
                    caption_content = self.format(
                        child, blanks_to_pars=True
                    )
                    with html("div"):
                        klass = "figure_caption"
                        if child.exists("center"):
                            klass += " figure_caption_center"
                        elif (
                            child.exists("nocenter")
                            or len(child.text_content) > 90
                        ):
                            klass += " figure_caption_nocenter"
                        doc.attr(klass=klass)
                        if label is not None:
                            with html(
                                "a",
                                klass="figure_caption_anchor",
                                href="#" + self.label2id(label),
                            ):
                                text(
                                    join_nonempty(
                                        self.localize("Fig."),
                                        tag.get("number"),
                                    )
                                )
                            text(": ")
                        else:
                            text(
                                join_nonempty(
                                    self.localize("Fig."),
                                    tag.get("number"),
                                )
                                + ": "
                            )
                        doc.asis(caption_content)
        return doc.getvalue()

    def handle_pythonvideo(self, tag: QqTag) -> str:
        """
        Uses tags: pythonvideo, style, jsanimate

        :param tag:
        :return:
        """

        if tag.exists("jsanimate"):
            return self.make_python_jsanimate(tag.text_content)

        path = self.make_python_fig(
            tag.text_content, exts=("mp4",), video=True
        )
        doc, html, text = Doc().tagtext()
        with html(
            "video",
            klass="figure img-responsive",
            controls="",
        ):
            if tag.exists("style"):
                doc.attr(style=tag.style_.value)
            doc.stag(
                "source",
                src=self.url_for_figure(
                    path + "/" + self.default_figname + ".mp4"
                ),
                type="video/mp4",
            )
        return doc.getvalue()

    def handle_pythonfigure(self, tag: QqTag) -> str:
        """
        Uses tags: pythonfigure, style, imgformat

        :param tag:
        :return:
        """
        format = tag.get("imgformat", "svg")
        path = self.make_python_fig(tag.text_content, exts=(format,))
        doc, html, text = Doc().tagtext()
        with html(
            "img",
            klass="figure img-responsive",
            src=self.url_for_figure(
                path + "/" + self.default_figname + "." + format
            ),
        ):
            if tag.exists("style"):
                doc.attr(style=tag.style_.value)
        return doc.getvalue()

    def handle_pythoncode(self, tag: QqTag) -> str:
        """
        Uses tags: pythoncode, clearglobals, donotrun

        :param tag:
        :return:
        """
        doc, html, text = Doc().tagtext()

        if tag.exists("showcode"):
            doc.asis(
                self.showcode(
                    tag,
                    collapsed=tag.exists("collapsed"),
                    lang="python",
                )
            )

        if tag.exists("clearglobals"):
            self.python_globals.clear()

        if not tag.exists("donotrun"):
            with stdout_io() as s:
                try:
                    exec(tag.text_content, self.python_globals)
                except Exception as e:
                    print(
                        "Exception: {}\n{}".format(e.__class__.__name__, e)
                    )
            with html("pre"):
                with html("code", klass="lang-python"):
                    doc.asis(s.getvalue())
        return doc.getvalue()

    def handle_plotly(self, tag: QqTag) -> str:
        return "".join(self.make_plotly_fig(tag.text_content))

    def handle_img(self, tag: QqTag) -> str:
        """
        Uses tags: src, style, alt

        :param tag:
        :return:
        """
        src = tag.src_.value
        doc, html, text = Doc().tagtext()
        with html(
            "img", klass="figure img-responsive", src=self.url_for_img(src)
        ):
            if tag.exists("style"):
                doc.attr(style=tag.style_.value)
            if tag.exists("alt"):
                doc.attr(alt=tag.alt_.value)
        return doc.getvalue()

    def showcode(
        self, tag: QqTag, collapsed=False, lang: str = None
    ) -> str:
        """
                <button class="source toggle btn btn-xs btn-primary">
        <span class="glyphicon glyphicon-chevron-up"></span>
        </button>

                :param tag:
                :param collapsed: show code in collapsed mode by default
                :param lang: language to use
                :return:
        """

        self.css["highlightjs"] = (
            '<link rel="stylesheet" '
            'href="https://cdnjs.cloudflare.com/ajax/libs/'
            'highlight.js/9.2.0/styles/default.min.css">\n'
            '<style type="text/css">\n'
            ".hljs {background: inherit;}\n"
            "</style>\n"
        )
        self.js_top["highlightjs"] = (
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/'
            'highlight.js/10.5.0/highlight.min.js"></script>\n'
            "<script>hljs.initHighlightingOnLoad();</script>\n"
            '<script charset="UTF-8" src="https://cdnjs.cloudflare.com/'
            'ajax/libs/highlight.js/10.5.0/languages/latex.min.js"></script>\n'
        )
        self.js_onload[
            "highlightjs"
        ] = """
        function toggle_block(obj, show) {
          var span = obj.find('span');
          if(show === true){
            span.removeClass('glyphicon-chevron-up')
                .addClass('glyphicon-chevron-down');
            obj.next('pre').slideDown();
          }
          else {
            span.removeClass('glyphicon-chevron-down')
                .addClass('glyphicon-chevron-up');
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
            button = button.replace(
                "glyphicon-chevron-up", "glyphicon-chevron-down"
            )

        doc, html, text = Doc().tagtext()
        with html("pre"):
            if collapsed:
                doc.attr(style="display:none")
            with html("code"):
                if lang:
                    doc.attr(klass="lang-" + lang)

                doc.asis(self.code_prefixes.get(tag.name, ""))
                # add a prefix if exists

                text(tag.text_content)

        return (
            "<div style='text-align: left'>"
            + button
            + doc.getvalue()
            + "</div>"
        )

    def handle_snippet(self, tag: QqTag) -> str:
        """
        Uses tags: hidden, backref, label

        :param tag:
        :return:
        """
        anchor = ""
        if not tag.exists("backref") and tag.exists("label"):
            anchor = "<span id='{}'></span>".format(
                self.label2id(tag.label_.value)
            )
        if tag.exists("hidden"):
            return anchor
        return anchor + self.format(tag, blanks_to_pars=True)

    def handle_alert(self, tag: QqTag) -> str:
        """
        Uses tags: alert, type

        :param tag:
        :return:
        """

        type = tag.get("type", "warning")

        return dedent(
            f"""<div class = 'alert alert-{type}'>
                {self.format(tag)}
            </div>"""
        )

    def handle_hide(self, tag: QqTag) -> str:
        """
        :param tag:
        :return: str
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

    def handle_tt(self, tag: QqTag) -> str:
        """
        Example:
            In Python it corresponds to \tt{bool} type.
        :param tag:
        :return:
        """
        return "<code>" + self.format(tag) + "</code>"

    def handle_emph(self, tag: QqTag) -> str:
        """
        Alias for em
        :param tag:
        :return:
        """
        return self.handle_em(tag)

    def handle_strong(self, tag: QqTag) -> str:
        """
        Makes text strong (i.e. bold face)
        :param tag:
        :return:
        """
        return "<strong>" + self.format(tag) + "</strong>"

    def handle_preformatted(self, tag: QqTag) -> str:
        r"""
        preformatted tag, like <pre> in HTML or \verbatim in LaTeX
        Uses tags: collapsed, lang

        :param tag:
        :return:
        """
        if not tag.exists("lang"):
            return "<pre>" + tag.text_content + "</pre>"
        else:
            return self.showcode(
                tag,
                collapsed=tag.exists("collapsed"),
                lang=tag.get("lang"),
            )

    def get_counter_for_tag(self, tag: QqTag) -> Optional[Counter]:
        name = tag.name
        counters = self.counters
        while True:
            if tag.exists("nonumber"):
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

    def make_numbers(self, tag: QqTag) -> None:
        """
        Uses tags: number, label, nonumber, flabel

        :return:
        """
        for child in tag.children_tags():
            name = child.name
            if (
                name in self.counters or name in self.enumerateable_envs
            ) and not (child.find("number") or child.exists("nonumber")):
                counter = self.get_counter_for_tag(child)
                if counter is not None:
                    counter.increase()
                    child.append_child(QqTag({"number": str(counter)}))
                    if child.find("label"):
                        label = child.label_.value
                        self.label_to_number[label] = str(counter)
                        # self.label_to_title[label] = child.text_content
            if child.find("label") and child.find("number"):
                self.label_to_number[
                    child.label_.value
                ] = child.number_.value
            if child.find("label"):
                self.label_to_tag[child.label_.value] = child
            if child.find("flabel"):
                self.flabel_to_tag[child.flabel_.value.lower()] = child
            self.make_numbers(child)

    def find_tag_by_flabel(self, s: str) -> QqTag:
        flabel = process.extractOne(s.lower(), self.flabel_to_tag.keys())[
            0
        ]
        return self.flabel_to_tag.get(flabel)

    def make_chapters(self):
        for heading, *contents in split_by_predicate(
            self.root,
            predicate=lambda tag: (
                isinstance(tag, QqTag) and tag.name == "chapter"
            ),
            zero_delim=QqTag("_zero_chapter"),
        ):
            self.add_chapter(Chapter(heading, [heading] + contents))

    def tag2chapter(self, tag) -> int:
        """
        Returns the number of chapter to which tag belongs.

        Chapters are separated by `chapter` tag.
        Chapter before the first `chapter`
        tag has number zero.

        :param tag:
        :return:
        """

        eve = tag.get_eve()
        chapters = self.root("chapter")

        return next(
            (
                i - 1
                for i, chapter in enumerate(chapters, 1)
                if eve.idx < chapter.idx
            ),
            len(chapters),
        )

    def url_for_chapter(
        self, index=None, label=None, fromindex=None
    ) -> str:
        """
        Returns url for chapter. Either index or label of
        the target chapter have to be provided.
        Optionally, fromindex can be provided. In this case
        function will return empty string if
        target chapter coincides with current one.

        You can inherit from QqHTMLFormatter and override
        url_for_chapter_by_index and url_for_chapter_by_label too
        use e.g. Flask's url_for.
        """
        assert index is not None or label is not None
        if index is None:
            index = self.label_to_chapter[label]
        if fromindex is not None and fromindex == index:
            # we are already on the right page
            return ""
        if label is None:
            label = self.chapters[index].heading.find("label")
        if not label:
            return self.url_for_chapter_by_index(index)
        return self.url_for_chapter_by_label(label.value)

    def url_for_chapter_by_index(self, index):
        return "/chapter/index/" + urllib.parse.quote(str(index))

    def url_for_chapter_by_label(self, label):
        return "/chapter/label/" + urllib.parse.quote(label)

    def add_chapter(self, chapter: Chapter) -> None:
        if chapter.heading.find("label"):
            self.label_to_chapter[chapter.heading.label_.value] = len(
                self.chapters
            )
        self.chapters.append(chapter)

    def do_format(self) -> str:
        self.make_numbers(self.root)
        return self.format(self.root, blanks_to_pars=True)

    def tag_id(self, tag: QqTag) -> str:
        """
        Returns id of tag:
        - If it has label, it is label-based
        - If it does not have label, but have number, it is number-based
        :param tag:
        :return: str id
        """
        if tag.find("label"):
            return self.label2id(tag.label_.value)
        elif tag.find("number"):
            return self.label2id(
                tag.name + "_number_" + str(tag.number_.value)
            )
        else:
            return ""

    def mk_toc(self, maxlevel=2, chapter=None) -> str:
        """
        Makes TOC (Table Of Contents)

        :param maxlevel: maximum heading level to include to TOC
        (default: 2)
        :param chapter: if None, we assume to have whole document on
        the same page and TOC contains only local links.
        If present, it is equal to index of current chapter
        :return: str with HTML content of TOC
        """
        doc, html, text = Doc().tagtext()
        curlevel = 1

        curchapter = 0
        # chapter before first `chapter` has index 0

        with html("ul", klass="nav"):
            for child in self.root.children_tags():
                chunk = []
                if child.name in self.heading_to_level:
                    hlevel = self.heading_to_level[child.name]

                    # `chapter` heading marks new chapter, so increase
                    # curchapter counter
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

                    targetpage = self.url_for_chapter(
                        index=curchapter, fromindex=chapter
                    )

                    item_doc, item_html, item_text = Doc().tagtext()
                    with item_html(
                        "li",
                        klass=("toc_item toc_item_level_%i" % curlevel),
                    ):
                        with item_html(
                            "a",
                            href=(targetpage + "#" + self.tag_id(child)),
                        ):
                            item_text(
                                self.format(child, blanks_to_pars=False)
                            )
                    chunk.append(item_doc.getvalue())
                    doc.asis("".join(chunk))
        return doc.getvalue()

    def extract_toc(self, maxlevel=2) -> TOCItem:
        """
        \chapter Hello
        \section World
        \section This
        \subsection Haha
        \section Hoho
        \chapter Another
        \section Dada

        --->
        TOCItem(None,
        [
            TOCItem(None, []),
            TOCItem("chap:Hello", [
                TOCItem("sec:World", []),
                TOCItem("sec:This", [
                    TOCItem("ssec:Haha", [])
                ],
                TOCItem("sec:Hoho", [])
            ],
            TOCItem("chap:Another",[
                TOCItem("sec:Dada", [])
            ])
        ])

        \section This
        \chapter Hello
        \subsection Haha
        \section Hoho

        TOCItem(None,
        [
            TOCItem(None, [
                TOCItem("sec:This")
            ]),
            TOCItem("chap:Hello"), [
                TOCItem(None, [
                    TOCItem("ssec:Haha", [])
                ]),
                TOCItem("Hoho", [])
            ]
        ])

        :param maxlevel: maximal level of headings to include
                         (headings numeration starts with 1)
        :return:
        """

        toc = TOCItem(None)
        curitem = toc.spawn_child(None)

        curlevel = 1

        # loop invariant:
        # 1. all heading processed so far are added to toc
        # 2. curlevel == level of the last processed heading
        # 3. curitem is a TOCItem for the last processed heading
        # 4. depth of curitem == curlevel (depth of root is 0)

        for tag in self.root.children_tags():
            if tag.name in self.heading_to_level:
                hlevel = self.heading_to_level[tag.name]

                if hlevel > maxlevel:
                    continue

                # want to make curlevel == hlevel - 1
                # by going up and down on the tree

                # if curlevel < hlevel - 1: add fake levels
                for curlevel in range(curlevel + 1, hlevel):
                    curitem = curitem.spawn_child(None)

                # if curlevel >= hlevel, go to parent TOCItem
                # (curlevel - hlevel + 1) times
                for curlevel in range(curlevel - 1, hlevel - 2, -1):
                    curitem = curitem.parent

                assert curlevel == hlevel - 1

                curitem = curitem.spawn_child(tag)
                curlevel = hlevel
        return toc

    def format_toc(
        self, toc: TOCItem, fromchapter: int = None, tochapter: int = None
    ) -> FormattedTOCItem:
        """
        Formats toc obtained with extract_toc()

        :param toc:
        :param fromchapter: current chapter, if None,
                assuming all chapters are on one page
                and only local links presented
        :param tochapter: chapter we render now,
                          None if we render contents
                          for the whole book
        :return:
        """

        ftoc = FormattedTOCItem()
        if toc.tag:
            ftoc.string = self.format(toc.tag, blanks_to_pars=False)
            targetpage = self.url_for_chapter(
                index=tochapter, fromindex=fromchapter
            )
            ftoc.href = targetpage + "#" + self.tag_id(toc.tag)
            ftoc.tag = toc.tag
            ftoc.iscurchapter = toc.level == 1 and fromchapter == tochapter

        for i, heading in enumerate(toc.children):
            if toc.level == 0:
                tochapter = i

            ftoc.append_child(
                self.format_toc(
                    heading, fromchapter=fromchapter, tochapter=tochapter
                )
            )
        return ftoc

    @staticmethod
    def tag_hash_id(tag: QqTag) -> str:
        """
        Returns autogenerated tag id based on tag's contents.
        It's first 5 characters of MD5-hashsum of tag's content
        :return:
        """
        return hashlib.md5(
            repr(tag.as_list()).encode("utf-8")
        ).hexdigest()[:5]

    def handle_quiz(self, tag: QqTag) -> str:
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
        if not tag.exists("md5id"):
            tag.append_child(QqTag("md5id", [self.tag_hash_id(tag)]))
        template = Template(
            filename=os.path.join(self.templates_dir, "quiz.html")
        )
        return template.render(formatter=self, tag=tag)

    def handle_rawhtml(self, tag: QqTag) -> str:
        return tag.text_content

    def handle_meta(self, tag: QqTag) -> str:
        return self.format(tag, blanks_to_pars=False) + "\n<hr/>"

    def handle_author(self, tag: QqTag) -> str:
        doc, html, text = Doc().tagtext()
        with html("p", klass="meta meta-author"):
            doc.asis(self.format(tag, blanks_to_pars=False))
        return doc.getvalue()

    def handle_affiliation(self, tag: QqTag) -> str:
        doc, html, text = Doc().tagtext()
        with html(
            "span", klass="meta meta-author meta-author-affiliation"
        ):
            doc.asis(" (" + self.format(tag, blanks_to_pars=False) + ")")
        return doc.getvalue()

    def handle_link(self, tag: QqTag) -> str:
        doc, html, text = Doc().tagtext()
        with html("p", klass="meta meta-link"):
            if tag.exists("role"):
                doc.add_class("meta-link-" + tag.role_.value)
            if tag.exists("url"):
                with html("a", href=tag.url_.value):
                    doc.asis(self.format(tag, blanks_to_pars=False))
            else:
                doc.asis(self.format(tag, blanks_to_pars=False))
        return doc.getvalue()

    def handle_title(self, tag: QqTag) -> str:
        doc, html, text = Doc().tagtext()
        with html("h1", klass="meta meta-title"):
            doc.asis(self.format(tag, blanks_to_pars=False))
        return doc.getvalue()

    def handle_subtitle(self, tag: QqTag) -> str:
        doc, html, text = Doc().tagtext()
        with html("h2", klass="meta meta-subtitle"):
            doc.asis(self.format(tag, blanks_to_pars=False))
        return doc.getvalue()
