import unittest
from qqmbr.qqdoc import QqTag, QqParser
from qqmbr.qqhtml import QqHTMLFormatter


class TestQqTagMethods(unittest.TestCase):
    def test_create_qqtag(self):
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
                             """<h2 id="label_h2_number_1_1"><span class="section__number">1.1. </span>"""
                             """World\n</h2>"""))
