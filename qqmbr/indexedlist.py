from collections import MutableSequence, Sequence, Mapping
from sortedcontainers import SortedList


class IndexedList(MutableSequence):
    """
    IndexedList is a mixture of list and dictionary.
    Every element in IndexedList has a key and one can access perform search by key.

    The key is calculated in the following way:

    - ``str``: key is ``str`` (it is a special case)
    - ``list``: key is first element of the list or ``None`` if there the list is empty
    - ``dictionary``: if it has only one record, its key is a key, otherwise ``Sequence.Mapping`` is a key
    - any other object: we'll look for .__qqkey__() method, and fallback to ``str`` if fail

    The main purpose of this class is to provide effective BeautifulSoup-style navigation over the s-expression-like
    data structures
    """

    def __init__(self, *iterable):
        if len(iterable) == 1 and isinstance(iterable[0], Sequence):
            iterable = iterable[0]
        self._container = list(iterable)
        self._locator = {}
        self.update_index()

    def __delitem__(self, i):
        old_element = self._container[i]
        self._locator[self.get_key(old_element)].remove(i)
        for key, places in self._locator.items():
            for k, index in enumerate(places):
                if index >= i:
                    places[k] -= 1

        del self._container[i]

    def __getitem__(self, i):
        return self._container[i]

    def __len__(self):
        return len(self._container)

    def __setitem__(self, i, item):
        places = self._locator[self.get_key(self._container[i])]
        places.remove(i)

        self._container[i] = item

        self.add_index(i, item)

    def insert(self, i, x):
        for key, places in self._locator.items():
            for k in range(len(places)-1, -1, -1):
                if places[k] >= i:
                    places[k] += 1
                else:
                    break
        self._container.insert(i, x)
        self.add_index(i, x)

    def __str__(self):
        return str(self._container)

    def __repr__(self):
        return "IndexedList(%s)" % repr(self._container)

    def find_index(self, key):
        return self._locator[key][0]

    def find_all_index(self, key):
        return self._locator[key]

    def find_all(self, key):
        return [self._container[i] for i in self.find_all_index(key)]

    def find(self, key):
        return self._container[self.find_index(key)]

    def update_index(self):
        self._locator.clear()
        for i, item in enumerate(self._container):
            self.add_index(i, item)

    def add_index(self, i, item):
        key = self.get_key(item)
        if key not in self._locator:
            self._locator[key] = SortedList()
        self._locator[key].add(i)

    def is_consistent(self):
        for i, el in enumerate(self._container):
            if i not in self.find_all_index(self.get_key(el)):
                return False
        return True

    def __eq__(self, other):
        if isinstance(other, IndexedList):
            return self._container == other._container
        elif isinstance(other, Sequence):
            return self._container == other
        else:
            return False

    def get_key(self, item):
        if isinstance(item, str):
            return str
        elif isinstance(item, Sequence):
            if item:
                return item[0]
            else:
                return None
        elif isinstance(item, Mapping):
            if len(item) == 1:
                return list(item)[0]
            else:
                return Mapping
        else:
            try:
                ret = item.__qqkey__()
            except AttributeError:
                ret = str
        return ret



