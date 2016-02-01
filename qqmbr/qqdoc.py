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
        elif isinstance(children, Sequence):
            self.children = IndexedList(children)
        else:
            raise QqError("I don't know what to do with children " + str(children))

    def __repr__(self):
        if self.parent is None:
            return "QqTag(%s, %s)" % (repr(self.name), repr(self.children))
        else:
            return "QqTag(%s, %s, parent = %s)" % (repr(self.name), repr(self.children), repr(self.parent))


    def __str__(self):
        return "{%s : %s}" % (self.name, self.children)

    def __eq__(self, other):
        if other is None:
            return False
        return self.__dict__ == other.__dict__

    @property
    def is_simple(self):
        """
        Simple tags are those containing only one child
        :return:
        """
        return len(self.children) == 1

    @property
    def value(self):
        if self.is_simple:
            return self.children[0]
        raise QqError("More than one child, value is not defined")

    @value.setter
    def value(self, value):
        if self.is_simple:
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

    def as_list(self):
        ret = [self.name]
        for child in self.children:
            if isinstance(child, QqTag):
                ret.append(child.as_list())
            else:
                ret.append(child)
        return ret

    def append_child(self, child):
        self.children.append(child)
        child.parent = self

    def append_line(self, line):
        if line:
            self.children.append(line)

    def __getitem__(self, item):
        return self.children[item]

class StackElement(object):
    def __init__(self, tag, indent=0, bracket=None, bracket_counter=0):
        self.tag = tag
        self.indent = indent
        self.bracket = bracket
        self.bracket_counter = bracket_counter
    def __str__(self):
        return "<%s, %s, %s, %s>" % (self.tag.name, str(self.indent), self.bracket, str(self.bracket_counter))
    def __repr__(self):
        return "StackElement(%s, %s, %s, %s)" % (repr(self.tag),
                                                 repr(self.indent),
                                                 repr(self.bracket),
                                                 repr(self.bracket_counter))

class QqParser(object):
    def __init__(self, command_symbol='\\', command_regex=r'\\',
                 allowed_tags=None, tag_regex=r"(\w+)", allowed_inline_tags=None):
        self.command_symbol = command_symbol
        self.command_regex = command_regex
        if allowed_tags is None:
            self.allowed_tags = {}
        else:
            self.allowed_tags = allowed_tags
        self.tag_regex = tag_regex
        if allowed_inline_tags is None:
            self.allowed_inline_tags = self.allowed_tags
        else:
            self.allowed_inline_tags = allowed_inline_tags
        self._last_tag = None
        self._stack = None

    def pop_stack(self):
        self._last_tag = self._stack.pop()
        return self._last_tag

    def get_indent(self, s):
        m = re.match(r'\s*', s)
        beginning = m.group(0)
        if '\t' in beginning:
            raise QqError("No tabs allowed in QqDoc at the beginning of line!")
        m = re.match(r' *', s)
        return len(m.group(0))



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
        if isinstance(lines, str):
            lines = lines.splitlines()

        tree = QqTag('_root')
        stack = [StackElement(tree, self.get_indent(lines[0])-1)]
        self._stack = stack
        self._last_tag = stack[0]
        inline_mode = False

        current_indent = 0

        for i, line in enumerate(lines):


            if not line or line[-1] != '\n':
                line = line + "\n"

            indent_decreased = False
            indent = self.get_indent(line)
            lin = line.strip()

            if indent < current_indent:
                indent_decreased = True
                current_indent = indent

            if indent_decreased and inline_mode:
                raise QqError("Indent decreased during inline mode on line %i: %s", (i + 1, lin))


            if not inline_mode:
                while indent <= stack[-1].indent:
                    self.pop_stack()

            if indent_decreased and indent != self._last_tag.indent:
                raise QqError("Formatting error: unexpected indent on line %i: %s \n\
                (expected indent %i on tag %s, get indent %i, stack: %s)" % (i + 1,
                                                                             lin,
                                                                             self._last_tag.indent,
                                                                             self._last_tag.tag.name, indent, str(stack)))

            current_tag = stack[-1].tag

            if lin and lin[0] == self.command_symbol:
                m = re.match(self.command_regex + self.tag_regex, lin)
                if m:
                    tag = m.group(1)
                    if tag in self.allowed_tags:
                        if inline_mode:
                            raise QqError("New block tag open during inline mode on line %i: %s", (i + 1, lin))

                        new_tag = QqTag(tag, [])
                        current_tag.append_child(new_tag)
                        stack.append(StackElement(new_tag, indent))

                        if i < len(lines)-1 and self.get_indent(lines[i+1]) > indent:
                            current_indent = self.get_indent(lines[i+1])

                        continue
                        # TODO: extended syntax



            inlines = re.finditer(self.command_regex +
                                  r'(?P<tag>' + self.tag_regex + ')' +
                                  r'(?P<bracket>[\{\[])' +
                                  r"|[\{\[\]\}]", line)

            # inline tags or brackets

            cursor = current_indent

            for m in inlines:
                if inline_mode:
                    if m.group(0) == stack[-1].bracket:
                        stack[-1].bracket_counter += 1
                    elif m.group(0) == {'{':'}', '[':']'}[stack[-1].bracket]:
                        stack[-1].bracket_counter -= 1
                        if stack[-1].bracket_counter == 0:
                            # close current inline tag

                            current_tag.append_line(line[cursor: m.start()])
                            cursor = m.end()

                            self.pop_stack()
                            current_tag = stack[-1].tag
                            if stack[-1].bracket is None:
                                inline_mode = False

                inline_tag = m.group('tag')
                if inline_tag is not None:
                    if inline_tag in self.allowed_inline_tags:
                        inline_mode = True
                        current_tag.append_line(line[cursor: m.start()])

                        new_tag = QqTag(inline_tag, [])
                        current_tag.append_child(new_tag)
                        stack.append(StackElement(new_tag, indent=None,
                                                  bracket=m.group('bracket'),
                                                  bracket_counter=1))
                        current_tag = new_tag
                        cursor = m.end()

                    else:
                        if inline_mode and m.group(0) == stack[-1].bracket:
                            stack[-1].bracket_counter += 1


            # Append the rest of line to current tag
            current_tag.append_line(line[cursor:])

        return tree