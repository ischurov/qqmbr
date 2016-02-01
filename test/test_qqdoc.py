import unittest
from qqmbr.indexedlist import IndexedList
from qqmbr.qqdoc import QqTag, QqParser

class TestQqTagMethods(unittest.TestCase):
    def test_create_qqtag(self):
        q = QqTag({'a':'b'})
        self.assertEqual(q.name, 'a')
        self.assertEqual(q.value, 'b')

        q = QqTag('a', [
            QqTag('b', 'hello'),
            QqTag('c', 'world'),
            QqTag('b', 'this'),
            QqTag('--+-', [
                QqTag('b', 'way'),
                "this"
            ])])

        self.assertEqual(q.name, 'a')
        self.assertEqual(q._children, IndexedList([QqTag('b', ['hello']), QqTag('c', ['world']), QqTag('b', ['this']), QqTag('--+-', [QqTag('b', ['way']), 'this'])]))
        self.assertEqual(eval(repr(q)), q)
        self.assertEqual(q.as_list(), ['a', ['b', 'hello'],['c', 'world'], ['b', 'this'], ['--+-', ['b', 'way'], 'this']])

    def test_qqtag_accessors(self):
        q = QqTag('a', [
            QqTag('b', 'hello'),
            QqTag('c', 'world'),
            QqTag('b', 'this'),
            QqTag('--+-', [
                QqTag('b', 'way'),
                "this"
            ])])

        self.assertEqual(q._b.value, 'hello')
        self.assertEqual(q._c.value, 'world')
        self.assertEqual(q('b'), [QqTag('b', 'hello'), QqTag('b', 'this')])
        self.assertEqual(q.find('--+-')._b.value, 'way')
        self.assertEqual(q[0].value, 'hello')
        self.assertEqual(q[1].value, 'world')
        self.assertEqual(q[3][0].value, 'way')


class TestQqParser(unittest.TestCase):
    def test_block_tags1(self):
        doc = r"""Hello
\tag
    World
"""
        parser = QqParser(allowed_tags={'tag'})
        tree = parser.parse(doc)
        self.assertEqual(tree[0], "Hello\n")

        self.assertEqual(tree._tag.name, 'tag')
        self.assertEqual(tree._tag.value, 'World\n')

    def test_block_tags_nested(self):
        doc = r"""Hello
\tag
    World
    \othertag
        This
        Is
    A test
The end

Blank line before the end
"""
        parser = QqParser(allowed_tags={'tag', 'othertag'})
        tree = parser.parse(doc)
        self.assertEqual(tree[0], "Hello\n")
        self.assertEqual(tree._tag[0], "World\n")
        self.assertEqual(tree._tag._othertag._children, ["This\nIs\n"])
        self.assertEqual(tree._tag[2], 'A test\n')
        self.assertEqual(tree[2], 'The end\n\nBlank line before the end\n')
        self.assertEqual(tree._tag.parent, tree)
        self.assertEqual(tree._tag._othertag.parent, tree._tag)

    def test_block_additional_indent(self):
        doc = r"""Hello
\tag
    First
        Second
    Third
End"""
        parser = QqParser(allowed_tags={'tag'})
        tree = parser.parse(doc)
        self.assertEqual(tree._tag._children, ['First\n    Second\nThird\n'])

    def test_inline_tag1(self):
        doc = r"""Hello, \tag{inline} tag!
"""
        parser = QqParser(allowed_tags={'tag'})
        tree = parser.parse(doc)
        self.assertEqual(tree[0], 'Hello, ')
        self.assertEqual(tree._tag.value, 'inline')
        self.assertEqual(tree[2], ' tag!\n')

    def test_inline_tag2(self):
        doc = r"""Hello, \othertag{\tag{inline} tag}!
"""
        parser = QqParser(allowed_tags={'tag', 'othertag'})
        tree = parser.parse(doc)
        self.assertEqual(tree._othertag._tag.value, 'inline')
        self.assertEqual(tree.as_list(), ['_root', 'Hello, ', ['othertag', ['tag', 'inline'], ' tag'], '!\n'])

    def test_inline_tag3(self):
        doc = r"""Hello, \tag{
this is a continuation of inline tag on the next line

the next one\othertag{okay}}
"""
        parser = QqParser(allowed_tags={'tag', 'othertag'})
        tree = parser.parse(doc)
        self.assertEqual(tree.as_list(),[
            '_root', 'Hello, ',
            [
                'tag',
                '\nthis is a continuation of inline tag on the next line\n\nthe next one',
                [
                    'othertag',
                    'okay'
                ]
            ],
            '\n'
        ])

    def test_inline_tag4(self):
        doc = r"Hello, \tag{I'm [your{taggy}] tag} okay"
        parser = QqParser(allowed_tags={'tag', 'othertag'})
        tree = parser.parse(doc)
        self.assertEqual(tree.as_list(),[
            '_root', 'Hello, ',
            [
                'tag',
                "I'm [your{taggy}] tag"
            ],
            " okay\n"
        ])

    def test_block_and_inline_tags(self):
        doc = r"""Hello,
\tag
    I'm your \othertag{tag}
    \tag
        {
        \tag
            {
            this \tag{is a {a test}
            okay}
        }
    }
"""
        parser = QqParser(allowed_tags={'tag', 'othertag'})
        tree = parser.parse(doc)
        self.assertEqual(tree.as_list(),[
            '_root', 'Hello,\n',
            [
                'tag',
                "I'm your ",
                ['othertag', 'tag'],
                '\n',
                [
                    'tag',
                    '{\n',
                    [
                        'tag',
                        '{\nthis ',
                        [
                            'tag',
                            'is a {a test}\nokay',
                        ],
                        '\n'
                     ],
                    '}\n'
                ],
                '}\n'
            ]
        ])




