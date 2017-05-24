import sys
import os
from textwrap import dedent

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..'))

from qqmbr.ml import QqParser, QqTag
from qqmbr.qqlatex import QqLaTeXFormatter

import unittest

class TestQqlatex(unittest.TestCase):
    def test_section(self):
        text = dedent(r"""\
            \h1 Section Two
            Some text
        """)
        formatter = QqLaTeXFormatter()
        parser = QqParser(allowed_tags=formatter.uses_tags())
        tree = parser.parse(text)
        formatter.root = tree
        obtained = formatter.format(tree)
        expected = dedent(r"""\
            \section{Section Two}
            Some text
        """)
        self.assertEquals(obtained, expected)


    def test_cross_reference(self):
        text = dedent(r"""\
            \h1 Proof of \ref[Theorem|thm:main]
            Some text
        """)
        formatter = QqLaTeXFormatter()
        parser = QqParser(allowed_tags=formatter.uses_tags())
        tree = parser.parse(text)
        formatter.root = tree
        obtained = formatter.format(tree)
        expected = dedent(r"""\
            \section{Proof of Theorem \ref{thm:main}}
            Some text
        """)
        self.assertEquals(obtained, expected)