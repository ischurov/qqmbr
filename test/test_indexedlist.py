# (c) Ilya V. Schurov, 2016
# Available under MIT license (see LICENSE file in the root folder)

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'qqmbr'))

from indexedlist import IndexedList

import unittest

from sortedcontainers import SortedList

class TestIndexedlistMethods(unittest.TestCase):

    def test_creating_indexedlist1(self):
        q = IndexedList([['a', 'b'], ['a', 'd']])
        self.assertEqual(list(q._locator['a']), [0, 1])
        self.assertTrue(q.is_consistent())


    def test_creating_indexedlist2(self):
        q = IndexedList(['a', 'b'], {'a': 123}, 'a', 123, ['a', 'b', 'c'], ['b', 123], ['a'], {'b': 321})
        self.assertEqual(repr(q), "IndexedList([['a', 'b'], {'a': 123}, 'a', 123, ['a', 'b', 'c'], ['b', 123], ['a'], {'b': 321}])")
        self.assertEqual(eval(repr(q)), q)
        self.assertEqual(q._locator, {'b': SortedList([5, 7]),
                                   'a': SortedList([0, 1, 4, 6]),
                                      str: SortedList([2, 3])})
        self.assertTrue(q.is_consistent())

    def test_delitem(self):
        q = IndexedList(['a', 'b'], {'a': 123}, 'a', 123, ['a', 'b', 'c'], ['b', 123], ['a'], {'b': 321})

        del q[0]
        self.assertEqual(q._locator,
                         {'b': SortedList([4, 6]),
                          'a': SortedList([0, 3, 5]),
                          str: SortedList([1, 2])})
        self.assertTrue(q.is_consistent())

        del q[2]
        self.assertEqual(q._locator,
                         {'b': SortedList([3, 5]),
                         'a': SortedList([0, 2, 4]),
                         str: SortedList([1])})
        self.assertTrue(q.is_consistent())

        del q[3]
        self.assertEqual(q._locator,
                         {'b': SortedList([4]),
                         'a': SortedList([0, 2, 3]),
                         str: SortedList([1])})

        self.assertTrue(q.is_consistent())

        del q[0]
        self.assertTrue(q.is_consistent())

        del q[3]
        self.assertTrue(q.is_consistent())

        del q[0]
        self.assertTrue(q.is_consistent())

        del q[1]
        self.assertTrue(q.is_consistent())

        del q[0]
        self.assertTrue(q.is_consistent())
        self.assertEqual(q, [])

    def test_setitem(self):
        q = IndexedList(['a', 'b'], {'a': 123}, 'a', 123, ['a', 'b', 'c'], ['b', 123], ['a'], {'b': 321})
        q[0] = 2
        self.assertEqual(q._locator,
                         {'b': SortedList([5, 7]),
                         'a': SortedList([1, 4, 6]),
                         str: SortedList([0, 2, 3])})

        self.assertTrue(q.is_consistent())

        q[2] = ['b', 'c', 'd']
        self.assertEqual(q._locator,
                         {'b': SortedList([2, 5, 7]),
                         'a': SortedList([1, 4, 6]),
                         str: SortedList([0, 3])})
        self.assertTrue(q.is_consistent())

        q[1] = ['cd', 'efg', 12]
        self.assertEqual(q._locator,
                         {'a': SortedList([4, 6]),
                         'b': SortedList([2, 5, 7]),
                         'cd': SortedList([1]),
                         str: SortedList([0, 3])})
        self.assertTrue(q.is_consistent())

    def test_insert(self):
        q = IndexedList(['a', 'b'], {'a': 123}, 'a', 123, ['a', 'b', 'c'], ['b', 123], ['a'], {'b': 321})
        q.insert(2, 'b')
        self.assertEqual(q._locator, {'a': SortedList([0, 1, 5, 7]),
                                     'b': SortedList([6, 8]),
                                      str: SortedList([2, 3, 4])})
        self.assertTrue(q.is_consistent())

        q.insert(0, ['b', 123])
        self.assertEqual(q._locator, {'a': SortedList([1, 2, 6, 8]),
                                     'b': SortedList([0, 7, 9]),
                                      str: SortedList([3, 4, 5])})
        self.assertTrue(q.is_consistent())


if __name__ == '__main__':
    unittest.main()