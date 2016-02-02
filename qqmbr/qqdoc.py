from collections import Sequence
from qqmbr.indexedlist import IndexedList
import re

class QqError(Exception):
    pass

class QqTag(object):
    """
    QqTag is essentially an IndexedList with name attached.

    It provides BeautifulSoup-style navigation over its child:
    - ``tag.find('subtag')`` returns first occurrence of a child with name ``subtag``. (Note that
    in contrast with BeatifulSoup, this is not recursive: it searches only through tag's childrens.)
    - ``tag._subtag`` is a shortcut for ``tag.find('subtag')`` (works if ``subtag`` is valid identifier)
    - ``tag.find_all('subtag')`` returns all occurrences of tag with name 'subtag'
    - ``tag('subtag')`` is shortcut for ``tag.find_all('subtag')``

    If QqTag has only one child, it is called *simple*. Then its `.value` is defined. (Useful for access to property-like
    subtags.)
    """
    def __init__(self, name, children = None, parent = None):
        if isinstance(name, dict) and len(name) == 1:
            self.__init__(*list(name.items())[0], parent=parent)
            return

        self.name = name
        self.parent = parent

        if children is None:
            self._children = IndexedList()
        elif isinstance(children, str) or isinstance(children, int) or isinstance(children, float):
            self._children = IndexedList([children])
        elif isinstance(children, Sequence):
            self._children = IndexedList(children)
        else:
            raise QqError("I don't know what to do with children " + str(children))

    def __repr__(self):
        if self.parent is None:
            return "QqTag(%s, %s)" % (repr(self.name), repr(self._children))
        else:
            return "QqTag(%s, %s, parent = %s)" % (repr(self.name), repr(self._children), repr(self.parent.name))


    def __str__(self):
        return "{%s : %s}" % (self.name, self._children)

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
        return len(self) == 1

    @property
    def value(self):
        if self.is_simple:
            return self[0]
        raise QqError("More than one child, value is not defined, QqTag: %s" % str(self))

    @value.setter
    def value(self, value):
        if self.is_simple:
            self[0] = value
        else:
            raise QqError("More than one child, cannot set value")


    def __qqkey__(self):
        return self.name

    def __getattr__(self, attr):
        if attr[0] == "_":
            return self.find(attr[1:])
        raise AttributeError()

    def find(self, key):
        if key in self._children._locator:
            return self._children.find(key)

    def find_all(self, key):
        if key in self._children._locator:
            return self._children.find_all(key)

    def __call__(self, key):
        return self.find_all(key)

    def as_list(self):
        ret = [self.name]
        for child in self:
            if isinstance(child, QqTag):
                ret.append(child.as_list())
            else:
                ret.append(child)
        return ret

    def append_child(self, child):
        self._children.append(child)
        child.parent = self

    def append_line(self, line):
        if line:
            self._children.append(line)

    def __getitem__(self, item):
        return self._children[item]

    def __setitem__(self, key, value):
        self._children[key] = value

    def __iter__(self):
        return iter(self._children)

    def __len__(self):
        return len(self._children)


    @property
    def text_content(self):
        chunk = []
        for child in self:
            if isinstance(child, str):
                chunk.append(child)
        return "".join(chunk)


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

    def str_stack(self):
        return ", ".join(str(s) for s in self._stack)

    @staticmethod
    def get_indent(s):
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
        """
        if isinstance(lines, str):
            lines = lines.splitlines(keepends=True)

        lines.reverse()
        numbers = list(range(len(lines), 0, -1))
        # We probably will append some elements to lines and have to maintain their numbers for error messages

        tree = QqTag('_root')
        stack = [StackElement(tree, self.get_indent(lines[-1])-1)]
        self._stack = stack
        self._last_tag = stack[0]
        current_tag = stack[0].tag
        inline_mode = False

        current_indent = self.get_indent(lines[-1])

        chunk = []


        while lines:
            line = lines.pop()
            i = numbers.pop()

        #    if not line or line[-1] != '\n':
        #        line += "\n"

            if line.strip() == "":
                line = " "*current_indent+"\n"

            indent_decreased = False
            indent = self.get_indent(line)
            lin = line.strip()

            if indent < current_indent:
                indent_decreased = True
                current_indent = indent

            if indent_decreased and inline_mode:
                raise QqError("Indent decreased during inline mode on line %i: %s", (i, lin))

            if not inline_mode:
                if indent <= stack[-1].indent:
                    current_tag.append_line("".join(chunk))
                    chunk = []

                while indent <= stack[-1].indent:
                    self.pop_stack()

            if indent_decreased and indent != self._last_tag.indent:
                raise QqError("Formatting error: unexpected indent on line %i: %s \n\
                (expected indent %i on tag %s, get indent %i, stack: %s)" % (i,
                                                                             lin,
                                                                             self._last_tag.indent,
                                                                             self._last_tag.tag.name, indent, self.str_stack()))

            current_tag = stack[-1].tag

            # Process block tags

            if lin and lin[0] == self.command_symbol:
                m = re.match(self.command_regex + self.tag_regex + r"(?![\[\{])", lin)
                if m:
                    tag = m.group(1)
                    if tag in self.allowed_tags:
                        if inline_mode:
                            raise QqError("New block tag open during inline mode on line %i: %s", (i, lin))

                        new_tag = QqTag(tag, [])

                        current_tag.append_line("".join(chunk))
                        chunk = []

                        current_tag.append_child(new_tag)

                        stack.append(StackElement(new_tag, indent))


                        if len(lines)>0 and self.get_indent(lines[-1]) > indent:
                            current_indent = self.get_indent(lines[-1])
                            tag_indent = current_indent
                        else:
                            tag_indent = self.get_indent(line) + 4
                        # virtual tag indent

                        rest = lin[m.end():]
                        restlines = [" "*tag_indent + l.lstrip() for l in rest.split('|') if l.strip() != ""]
                        if restlines:
                            current_indent = tag_indent
                        for restline in reversed(restlines):
                            lines.append(restline)
                            numbers.append(i)

                        continue


            # Process inline tags

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
                    elif m.group(0) == {'{': '}', '[': ']'}[stack[-1].bracket]:
                        stack[-1].bracket_counter -= 1
                        if stack[-1].bracket_counter == 0:
                            # close current inline tag

                            # TODO: Special handlers for [] tags (e.g. short references syntax etc.)

                            chunk.append(line[cursor: m.start()])
                            current_tag.append_line("".join(chunk))
                            chunk = []

                            cursor = m.end()

                            self.pop_stack()
                            current_tag = stack[-1].tag
                            if stack[-1].bracket is None:
                                inline_mode = False

                inline_tag = m.group('tag')
                if inline_tag is not None:
                    if inline_tag in self.allowed_inline_tags:
                        inline_mode = True
                        chunk.append(line[cursor: m.start()])
                        current_tag.append_line("".join(chunk))
                        chunk = []

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
            chunk.append(line[cursor:])

        current_tag.append_line("".join(chunk))

        return tree