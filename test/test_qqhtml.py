# (c) Ilya V. Schurov, 2016
# Available under MIT license (see LICENSE file in the root folder)

import unittest
from qqmbr.qqdoc import QqParser
from qqmbr.qqhtml import QqHTMLFormatter
from bs4 import BeautifulSoup


class TestQqHtmlMethods(unittest.TestCase):
    def test_parse_html1(self):
        parser = QqParser(allowed_tags={'h1', 'h2', 'h3', 'h4', 'eq', 'eqref', 'ref', 'equation', 'label', 'idx'})
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
        self.assertEqual(s, ("""<h1 id="label_h1_label"><span class="section__number">1. </span>Hello\n</h1>"""
                             """<h2 id="label_h2_number_1"><span class="section__number">1. </span>"""
                             """World\n</h2>"""))

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
        self.assertEqual(soup.span.string, "1. ")
        self.assertEqual(soup.a.attrs,{'class': ['a-ref'], 'title': 'Hello\n\n', 'href': '#label_h1_label'})
        self.assertEqual(soup.a.string, "1")

    def test_parse_html3(self):
        parser = QqParser(allowed_tags={'h1', 'h2', 'h3', 'h4', 'eq', 'eqref', 'ref', 'equation', 'label', 'idx'})
        doc = r"""\equation \label eq:x2y2
    x^2 + y^2 = z^2

See \ref{eq:x2y2}.
"""
        tree = parser.parse(doc)
        html = QqHTMLFormatter(tree)
        s = html.do_format()
        soup = BeautifulSoup(s, 'html.parser')
        self.assertEqual(soup.div.attrs, {'id':"label_eq_x2y2",'class':["latex_equation"]})
        self.assertEqual(soup.span['class'], ['ref'])
        self.assertEqual(soup.a['class'], ['a-ref'])
        self.assertEqual(soup.a['href'], '#label_eq_x2y2')
        self.assertEqual(soup.a.string, "(1)")






