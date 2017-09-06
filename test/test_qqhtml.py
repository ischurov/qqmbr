# (c) Ilya V. Schurov, 2016
# Available under MIT license (see LICENSE file in the root folder)

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from indentml.parser import QqParser, QqTag
from qqmbr.qqhtml import QqHTMLFormatter

import unittest
from bs4 import BeautifulSoup
import os
import contextlib


# FROM: http://code.activestate.com/recipes/576620-changedirectory-context-manager/
# BY: Greg Warner

@contextlib.contextmanager
def working_directory(path):
    """A context manager which changes the working directory to the given
    path, and then changes it back to its previous value on exit.

    """
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)
# END FROM


class TestQqHtmlMethods(unittest.TestCase):
    def test_parse_html1(self):
        parser = QqParser(allowed_tags={'h1', 'h2', 'h3', 'h4', 'eq',
                                        'eqref', 'ref', 'equation',
                                        'label', 'idx'})
        doc = r"""\h1
    Hello
    \label
        h1:label
\h2
    World
"""
        tree = parser.parse(doc)
        html = QqHTMLFormatter(tree)
        s = html.do_format()
        print(s)
        soup = BeautifulSoup(s, 'html.parser')

        #self.assertEqual(s, """<h1 id="label_h1_label"><span class="section__number"><a href="#label_h1_label" class="section__number">1</a></span>Hello
#</h1><h2 id="label_h2_number_1_1"><span class="section__number"><a href="#label_h2_number_1_1" class="section__number">1.1</a></span>World
#</h2>""")

        self.assertEqual('label_h1_label', soup.h1['id'])
        self.assertEqual(['section__number'], soup.span['class'])
        self.assertEqual('#label_h1_label', soup.a['href'])
        self.assertEqual(['section__number'], soup.a['class'])
        self.assertEqual('1Hello', soup.h1.text.strip())
        self.assertEqual('1.1World', soup.h2.text.strip())

    def test_parse_html2(self):
        parser = QqParser(allowed_tags={'h1', 'h2', 'h3', 'h4', 'eq', 'eqref', 'ref', 'equation', 'label', 'idx'})
        doc = r"""\h1 \label h1:label
    Hello

This is a \ref{h1:label}.
"""
        tree = parser.parse(doc)
        html = QqHTMLFormatter(tree)
        s = html.do_format()
        soup = BeautifulSoup(s, 'html.parser')

        self.assertEqual(soup.h1['id'], 'label_h1_label')
        self.assertEqual(soup.span['class'], ['section__number'])
        self.assertEqual(soup.span.string, "1")
        self.assertEqual(soup("a")[1].attrs,{'class': ['a-ref'], 'title': '', 'href': '#label_h1_label'})
        self.assertEqual(soup("a")[1].string, "1")

    def test_parse_html3(self):
        parser = QqParser(allowed_tags={'h1', 'h2', 'h3', 'h4', 'eq', 'eqref', 'ref', 'equation', 'label', 'idx'})
        doc = r"""\equation \label eq:x2y2
    x^2 + y^2 = z^2

See \ref{eq:x2y2}.
"""
        tree = parser.parse(doc)
        html = QqHTMLFormatter(tree)
        html.counters['equation'].showparents = False
        s = html.do_format()
        soup = BeautifulSoup(s, 'html.parser')
        self.assertEqual(soup.div.attrs, {'id':"label_eq_x2y2",'class':["latex_equation"]})
        self.assertEqual(soup.span['class'], ['ref'])
        self.assertEqual(soup.a['class'], ['a-ref'])
        self.assertEqual(soup.a['href'], '#mjx-eqn-1')
        self.assertEqual(soup.a.string, "(1)")

    def test_parse_html_math_align(self):

        html = QqHTMLFormatter()
        parser = QqParser(allowed_tags=html.uses_tags())

        doc = r"""\align
    \item c^2 &= a^2 + b^2 \label eq:one
    \item c &= \sqrt{a^2 + b^2} \label eq:two


See \ref{eq:one} and \ref{eq:two}
"""
        tree = parser.parse(doc)
        html.root = tree
        html.counters['equation'].showparents = False
        s = html.do_format()
        soup = BeautifulSoup(s, 'html.parser')
        print(repr(soup.text))
        self.assertEqual(soup.text, "\\[\n\\begin{align}\n\nc^2 &= a^2 + b^2 \n\\tag{1}\n\\\\\n"
                                    "c &= \\sqrt{a^2 + b^2} \n\\tag{2}\n\\\\\n\\end{align}\n\\]\n\n\n\nSee (1) and (2)")
        self.assertEqual(soup.a['href'], "#mjx-eqn-1")
        self.assertEqual(soup.a.string, "(1)")
        self.assertEqual(soup("a")[1]['href'], "#mjx-eqn-2")
        self.assertEqual(soup("a")[1].string, "(2)")

    def test_tag2chapter(self):
        html = QqHTMLFormatter()
        parser = QqParser(allowed_tags=html.uses_tags())
        parser.allowed_tags.add('author')
        doc = r"""\author Ilya V. Schurov
\h1 Chapter 1
This is the first chapter
\equation \label eq1
    x^2 + y^2

\h1 Chapter 2
This is the second chapter
\h2 Section 1
Hello
\remark \label rem
    This is the end. \ref{eq1}
"""
        tree = parser.parse(doc)
        html.root = tree
        self.assertEqual(html.tag2chapter(tree._author), 0)
        self.assertEqual(html.tag2chapter(tree._equation), 1)
        self.assertEqual(html.tag2chapter(tree._equation._label), 1)
        self.assertEqual(html.tag2chapter(tree._remark), 2)
        self.assertEqual(html.tag2chapter(tree._remark._ref), 2)

    def test_ref_with_separator(self):
        doc = r"""\h1 Hello \label sec:first

See \ref[section][sec:first] for details.
"""
        parser = QqParser()
        formatter = QqHTMLFormatter()
        parser.allowed_tags.update(formatter.uses_tags())
        tree = parser.parse(doc)
        formatter.root = tree
        html = formatter.do_format()
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(soup("a")[1]['href'], "#label_sec_first")
        self.assertEqual(soup("a")[1].string, "section 1")

    def test_refs_with_separator(self):
        doc = r"""\h1 Hello \label sec:first

\h1 World \label sec:other

See
\ref[section][sec:first] and \ref[section][sec:other] for details.
"""
        parser = QqParser()
        formatter = QqHTMLFormatter()
        parser.allowed_tags.update(formatter.uses_tags())
        tree = parser.parse(doc)
        formatter.root = tree
        print(tree.as_list())
        html = formatter.do_format()
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(soup("a")[2].contents[0], "section 1")








