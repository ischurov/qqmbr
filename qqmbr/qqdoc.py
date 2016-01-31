from collections import Sequence, namedtuple
from qqmbr.indexedlist import IndexedList
import re

class QqError(Exception):
    pass

class QqTag(object):
    def __init__(self, name, children = None, parent = None):
        if isinstance(name, dict) and len(name) == 1:
            self.__init__(*list(name.items())[0], parent=parent)
            return

        self.name = name
        self.parent = parent

        if children is None:
            self.children = IndexedList()
        elif isinstance(children, str) or isinstance(children, int) or isinstance(children, float):
            self.children = IndexedList([children])
        elif isinstance(children, Sequence) and type(children) != IndexedList:
            self.children = IndexedList(children)
        else:
            raise QqError("I don't know what to do with children " + str(children))

    def __repr__(self):
        return "QqTag(%s, %s)" % (repr(self.name), self.children)

    def __str__(self):
        return "{%s : %s}" % (self.name, self.children)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def is_simple(self):
        """
        Simple tags are those containing only one child
        :return:
        """
        return len(self.children) == 1

    @property
    def value(self):
        if self.is_simple():
            return self.children[0]
        raise QqError("More than one child, value is not defined")

    @value.setter
    def value(self, value):
        if self.is_simple():
            self.children[0] = value
        else:
            raise QqError("More than one child, cannot set value")


    def __qqkey__(self):
        return self.name

    def __getattr__(self, attr):
        if attr[0] == "_":
            return self.find(attr[1:])
        raise AttributeError()

    def find(self, key):
        if key in self.children._locator:
            return self.children.find(key)

    def find_all(self, key):
        if key in self.children._locator:
            return self.children.find_all(key)

    def __call__(self, key):
        return self.find_all(key)

class QqParser(object):
    def __init__(self, command_symbol='\\', command_regexp=r'\\', allowed_tags=None):
        self.command_symbol = command_symbol
        self.command_regexp = command_regexp
        if allowed_tags is None:
            self.allowed_tags = {}
        else:
            self.allowed_tags = allowed_tags

    def get_indent(self, s):
        m = re.match(r'\s*', s)
        beginning = m.group(0)
        if '\t' in beginning:
            raise QqError("No tabs allowed in QqDoc at the beginning of line!")
        return len(beginning)



    def parse(self, lines):
        """
        :param lines:
        :return:

        == Example ==

        line with indent 0 (belong to root)
        \tag with indent 0 (belong to root)
            line with indent 4 (belong to tag)
        line with indent 0 (belong to root)
        """
        tree = QqTag('_root')
        StackElement = namedtuple('StackElement', ['tag', 'indent'])
        stack = [StackElement(tree, self.get_indent(lines[0])-1)]
        last_tag = stack[-1]

        for i, line in enumerate(lines, 1):
            indent = self.get_indent(line)
            lin = line.strip()

            while indent <= stack[-1].indent:
                last_tag = stack.pop()

#            if indent > 0 and indent != last_tag.indent:
#                raise QqError("Formatting error: indent doesn't match on line %i: %s" % (i, lin))

            current_tag = stack[-1].tag

            if lin and lin[0] == self.command_symbol:
                m = re.match(self.command_regexp+r"(\w+)", lin)
                if m:
                    tag = m.group(1)
                    if tag in self.allowed_tags:
                        new_tag = QqTag(tag, [], parent=current_tag)
                        current_tag.children.append(new_tag)
                        stack.append(StackElement(new_tag, indent))

                        continue
                        # TODO: extended syntax

            # Ordinary line, not a tag
            # Append it to current tag
            current_tag.children.append(line)

        return tree










