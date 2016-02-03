# (c) Ilya V. Schurov, 2016
# Available under MIT license (see LICENSE file in the root folder)

import unittest
from qqmbr.qqdoc import QqParser
from qqmbr.qqhtml import QqHTMLFormatter


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
