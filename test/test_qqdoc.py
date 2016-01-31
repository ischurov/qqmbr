import unittest
from qqmbr.indexedlist import IndexedList
from sortedcontainers import SortedList
from qqmbr.qqdoc import QqTag

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
        self.assertEqual(q.children, IndexedList([QqTag('b', ['hello']), QqTag('c', ['world']), QqTag('b', ['this']), QqTag('--+-', [QqTag('b', ['way']), 'this'])]))
        self.assertEqual(eval(repr(q)), q)

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


