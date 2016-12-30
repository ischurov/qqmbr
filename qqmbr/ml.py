# (c) Ilya V. Schurov, 2016
# Available under MIT license (see LICENSE file in the root folder)

from collections import Sequence, MutableSequence
from indexedlist import IndexedList
import re
import os


class QqError(Exception):
    pass


class QqTag(MutableSequence):
    """
    QqTag is essentially an IndexedList with name attached. It behaves
    mostly like eTree Element.

    It provides eTree and BeautifulSoup-style navigation over its child:
    - ``tag.find('subtag')`` returns first occurrence of a child with name
      ``subtag``. (Note that in contrast with BeautifulSoup, this is not
      recursive: it searches only through tag's direct childrens.)
    - ``tag._subtag`` is a shortcut for ``tag.find('subtag')``
      (works if ``subtag`` is valid identifier)
    - ``tag.find_all('subtag')`` returns all occurrences of tag with
      name 'subtag'
    - ``tag('subtag')`` is shortcut for ``tag.find_all('subtag')``

    If QqTag has only one child, it is called *simple*. Then its `.value`
    is defined. (Useful for access to property-like subtags.)
    """
    def __init__(self, name, children=None, parent=None, index=None,
                 adopt=False):
        if isinstance(name, dict) and len(name) == 1:
            self.__init__(*list(name.items())[0], parent=parent)
            return

        self.name = name
        self.parent = parent
        self.index = index
        # tag has to know its place in the list of parents children
        # to be able to navigate to previous / next siblings

        self.adopter = adopt
        # tag is called 'adopter' if it does not register itself as
        # a parent of its children
        # TODO: write test for adoption

        if children is None:
            self._children = IndexedList()
        elif (isinstance(children, str) or isinstance(children, int) or
              isinstance(children, float)):
            self._children = IndexedList([children])
        elif isinstance(children, Sequence):
            self._children = IndexedList(children)
        else:
            raise QqError("I don't know what to do with children " +
                          str(children))

        if not adopt:
            for i, child in enumerate(self):
                if isinstance(child, QqTag):
                    child.parent = self
                    child.index = i

    def __repr__(self):
        if self.parent is None:
            return "QqTag(%s, %s)" % (repr(self.name),
                                      repr(self._children))
        else:
            return "QqTag(%s, %s, parent = %s)" % (repr(self.name),
                                                   repr(self._children),
                                                   repr(self.parent.name))

    def __str__(self):
        return "{%s : %s}" % (self.name, self._children)

    def __eq__(self, other):
        if other is None or not isinstance(other, QqTag):
            return False
        return self.as_list() == other.as_list()

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
            return self[0].strip()
        raise QqError(
            "More than one child, value is not defined, QqTag: " +
            str(self))

    @value.setter
    def value(self, value):
        if self.is_simple:
            self[0] = value
        else:
            raise QqError("More than one child, cannot set value")

    def qqkey(self):
        return self.name

    def __getattr__(self, attr):
        if attr[0] == "_":
            return self.find(attr[1:])
        raise AttributeError("Attribute " + attr + " not found")

    def find(self, key):
        """
        Returns direct children with the given key if it exists,
        otherwise returns None
        :param key: key
        :return: QqTag
        """
        if key in self._children._locator:
            return self._children.find(key)

    def find_all(self, key):
        return QqTag("_", self._children.find_all(key), adopt=True)

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

    def insert(self, index: int, child) -> None:
        self._children.insert(index, child)
        if not self.adopter and isinstance(child, QqTag):
            # TODO: testme
            child.parent = self
            child.index = index
            for i in range(index+1, len(self)):
                self._children[i].index += 1

    def __delitem__(self, index: int):
        del self._children[index]
        if not self.adopter:
            # TODO: testme
            for i in range(index, len(self)):
                self._children[i].index -= 1

    def append_child(self, child):
        self.insert(len(self), child)

    def _is_consistent(self):
        if self.adopter:
            raise QqError("Adopter cannot be checked for consistency")
        for i, child in enumerate(self):
            if child.parent != self or child.index != i:
                return False
        return True

    def append_line(self, line):
        if line:
            self._children.append(line)

    def __getitem__(self, item):
        return self._children[item]

    def __setitem__(self, index, child):
        self._children[index] = child
        if not self.adopter:
            #TODO testme
            child.parent = self
            child.index = index

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

    def exists(self, key):
        """
        Returns True if a child with given key exists
        :param key:
        :return:
        """
        return key in self._children._locator

    def get(self, key, default_value=None):
        """
        Returns a value of a direct child with a given key.
        If it is does not exists or is not simple, returns default value (default: None)
        :param key: key
        :param default_value: what to return if there is no such key or the corresponding child is ot simple
        :return: the value of a child
        """
        tag = self.find(key)
        if tag and tag.is_simple:
            return tag.value
        else:
            return default_value

    def ancestor_path(self):
        """
        Returns list of ancestors for self.

        Example:

            \tag
                \othertag
                    \thirdtag

        thirdtag.ancestor_path == [thirdtag, othertag, tag, _root]

        :return:
        """
        tag = self
        path = [tag]
        while tag.parent:
            tag = tag.parent
            path.append(tag)
        return path

    def get_eva(self):
        """
        Returns ancestor which is direct child of root

        :return:
        """
        return self.ancestor_path()[-2]

    def next(self):
        if (not self.parent or self.index is None or
                    self.index == len(self.parent) - 1):
            return None
        return self.parent[self.index + 1]

    def prev(self):
        if not self.parent or self.index is None or self.index == 0:
            return None
        return self.parent[self.index - 1]

    def process_separator(self, separator='separator', item='_item'):
        """
        If tag contains separator tag, tag's children will be reformatted
        in the following way:
        \tag
            something
            \separator
            something
            \subtag
                some content
            \separator
            other thing
        will be changed to
        \tag
            \item_
                something
            \item_
                something
                \subtag
                    some content
            \item_
                other thing
        If tag does not contain separator tag, exception will be raised
        :param separator: name of separator tag (default: 'separator'
        :param item: name of item tag (default: `_item`)
        :return: self
        """
        sep = QqTag(separator)
        if sep not in self:
            raise QqError("Tag {} does not contains separator {}".format(
                self, separator
            ))

        sep = QqTag(separator)
        children_list = list(self)
        # copy list of childrens

        self._children.clear()
        item_tag = QqTag(item)
        for child in children_list:
            if child == sep:
                self.append_child(item_tag)
                item_tag = QqTag(item)
            else:
                item_tag.append_child(child)
        self.append_child(item_tag)
        return self

    def process_separator_recursively(self, separator='separator',
                                      item='_item'):
        for child in self:
            if isinstance(child, str):
                continue
            if QqTag(separator) in child:
                child.process_separator(separator=separator, item=item)
            child.process_separator_recursively(separator=separator,
                                                item=item)

    def children_values(self, strings='raise', not_simple='raise'):
        """
        Make a list of .value applied to all children instances

        :param strings: one of 'raise', 'keep', 'none', 'skip'
        :param not_simple: one of 'raise', 'keep', 'none', 'skip'

        What to do if string or not simple tag occurs:
        - 'raise': raise an exception
        - 'keep': keep tags/strings as is
        - 'none': replace with None
        - 'skip': skip this item
        :return: list of strings
        """
        assert strings in ['raise', 'keep', 'none', 'skip']
        assert not_simple in ['raise', 'keep', 'none', 'skip']
        values = []
        for child in self:
            if isinstance(child, str):
                if strings == 'raise':
                    raise QqError(
                        "string does not have value (set strings option"
                        "to 'keep', 'none' or 'skip' to workaround)"
                    )
                if strings == 'keep':
                    values.append(child)
                elif strings == 'none':
                    values.append(None)
                # if strings == 'skip': pass
            else: # QqTag assumed
                if child.is_simple:
                    values.append(child.value)
                    continue
                # child is not simple
                if not_simple == 'raise':
                    raise QqError(
                        ("Child {} is not simple. Use not_simple option "
                         "to tweak the behavior").format(child))
                if not_simple == 'none':
                    values.append(None)
                # if not_simple == 'skip': pass
        return values


class StackElement(object):
    def __init__(self, tag, indent=0, bracket=None, bracket_counter=0):
        self.tag = tag
        self.indent = indent
        self.bracket = bracket
        self.bracket_counter = bracket_counter

    def __str__(self):
        return "<%s, %s, %s, %s>" % (self.tag.name, str(self.indent),
                                     self.bracket,
                                     str(self.bracket_counter))

    def __repr__(self):
        return "StackElement(%s, %s, %s, %s)" % (repr(self.tag),
                                                 repr(self.indent),
                                                 repr(self.bracket),
                                                 repr(self.bracket_counter))


class QqParser(object):
    """
    General MLQQ parser.
    """
    def __init__(self, tb_char='\\', sep_char="|",
                 allowed_tags=None, tag_regex=r"([^\s\{\[\|\&]+)", allowed_inline_tags=None, alias2tag=None,
                 separator='separator', include='include', include_dir = ''):
        self.tb_char = tb_char
        self.command_regex = re.escape(self.tb_char)
        if allowed_tags is None:
            self.allowed_tags = set([])
        else:
            self.allowed_tags = allowed_tags
        self.tag_regex = tag_regex
        if allowed_inline_tags is None:
            self.allowed_inline_tags = self.allowed_tags
        else:
            self.allowed_inline_tags = allowed_inline_tags
        self._last_tag = None
        self._stack = None
        if alias2tag is None:
            self.alias2tag = {}
        else:
            self.alias2tag = alias2tag
        self.escape_stub = '&_ESCAPE_Thohhe1eieMam6Yo_'
        self.sep_char = sep_char
        self.sep_regex = re.escape(self.sep_char)
        self.separator = separator
        self.separator_tag = self.tb_char + separator
        self.allowed_tags.add(separator)
        self.include = include
        self.allowed_tags.add(include)
        self.include_dir = include_dir

    def pop_stack(self):
        self._last_tag = self._stack.pop()
        return self._last_tag

    def str_stack(self):
        return ", ".join(str(s) for s in self._stack)

    def get_indent(self, s) -> int:
        m = re.match(r'\s*', s)
        beginning = m.group(0)
        if '\t' in beginning:
            raise QqError("No tabs allowed in QqDoc at the beginning of line!")
        m = re.match(r' *', s)
        return len(m.group(0))

    def escape_line(self, s):
        """
        Replaces '\\' and '\ ' with special stub
        :param s: a line
        :return: escaped line
        """
        s = s.replace(self.tb_char * 2, self.escape_stub + 'COMMAND_&')
        s = s.replace(self.tb_char + self.sep_char, self.escape_stub + 'SEP_&')
        s = s.replace(self.tb_char + " ", self.escape_stub + 'SPACE_&')
        s = s.replace(self.tb_char + "{", self.escape_stub + 'OPEN_CURVE_&')
        s = s.replace(self.tb_char + "[", self.escape_stub + 'OPEN_SQUARE_&')
        s = s.replace(self.tb_char + "}", self.escape_stub + 'CLOSE_CURVE_&')
        s = s.replace(self.tb_char + "]", self.escape_stub + 'CLOSE_SQUARE_&')


        return s

    def unescape_line(self, s):
        """
        Replaces special stub's inserted by ``escape_line()`` with '\' and ' '

        Note: this is **NOT** an inverse of escape_line.

        :param s: a line
        :return: unescaped line
        """
        s = s.replace(self.escape_stub + 'SPACE_&', " ")
        s = s.replace(self.escape_stub + 'SEP_&', self.sep_char)
        s = s.replace(self.escape_stub + 'COMMAND_&', self.tb_char)
        s = s.replace(self.escape_stub + 'OPEN_CURVE_&', '{')
        s = s.replace(self.escape_stub + 'OPEN_SQUARE_&', '[')
        s = s.replace(self.escape_stub + 'CLOSE_CURVE_&', '}')
        s = s.replace(self.escape_stub + 'CLOSE_SQUARE_&', ']')

        return s

    def split_line_by_tags(self, line):
        """
        something \subtag other | this \is \a \test
        -->
        something
        \subtag other
        \separator
        this
        \is
        \a
        \test

        :param line:
        :return:
        """
        sep = self.command_regex + "(" + self.tag_regex + r"(?!{))|" + self.sep_regex
        seps = re.finditer(sep, line)
        cursor = 0
        chunk = []
        for m in seps:
            tag = m.group(1)
            tag = self.alias2tag.get(tag, tag)
            if tag in self.allowed_tags:
                chunk.append(line[cursor: m.start()].lstrip())
                cursor = m.start()
            elif m.group(0) == self.sep_char:
                chunk.append(line[cursor: m.start()].lstrip())
                chunk.append(self.separator_tag)
                cursor = m.end()
        chunk.append(line[cursor:])
        return chunk

    def parse(self, lines):
        """
        :param lines:
        :return:
        """
        if isinstance(lines, str):
            lines = lines.splitlines(keepends=True)

        lines.reverse()
        numbers = list(range(len(lines), 0, -1))
        # We probably will append some elements to lines and have to
        # maintain their numbers for error messages

        tree = QqTag('_root')
        stack = [StackElement(tree, self.get_indent(lines[-1])-1)]
        self._stack = stack
        self._last_tag = stack[0]
        current_tag = stack[0].tag

        current_indent = self.get_indent(lines[-1])

        chunk = []
        chunknumbers = []

        while lines:

            skip = False

            line = self.escape_line(lines.pop())
            i = numbers.pop()

            if line.strip() == "":
                indent_line = " "*current_indent

                if len(line)>0 and line[-1] == "\n":
                    line = indent_line + "\n"
                else:
                    line = indent_line

            indent_decreased = False
            indent = self.get_indent(line)
            lin = line.lstrip()

            if indent < current_indent:
                indent_decreased = True
                current_indent = indent

            if indent_decreased and stack[-1].indent is None:
                raise QqError("Indent decreased during inline mode on line %i: %s", (i, lin))

            if stack[-1].indent is not None:
                if indent <= stack[-1].indent:
                    current_tag.append_line(self.unescape_line("".join(chunk)))
                    chunk = []

                while indent <= stack[-1].indent:
                    self.pop_stack()

            if indent_decreased and indent != self._last_tag.indent:
                raise QqError("Formatting error: unexpected indent on line %i: %s \n\
                (expected indent %i on tag %s, get indent %i, stack: %s)" % (i,
                                                                             lin,
                                                                             self._last_tag.indent,
                                                                             self._last_tag.tag.name, indent,
                                                                             self.str_stack()))

            current_tag = stack[-1].tag

            # Process block tags

            if lin and lin[0] == self.tb_char:
                m = re.match(self.command_regex + self.tag_regex + r"(?= |{}|$)".format(self.command_regex), lin)

                if m:
                    tag = m.group(1)
                    tag = self.alias2tag.get(tag, tag)
                    if tag in self.allowed_tags:
                        if stack[-1].indent is None:
                            raise QqError("New block tag open during inline mode on line %i: %s", (i, lin))

                        # process include tag
                        if tag == self.include:
                            filename = os.path.join(self.include_dir, lin[m.end():].strip())
                            with open(filename) as f:
                                includelines = f.readlines()
                            if includelines:
                                includeindent = self.get_indent(includelines[0])
                                for includeline in reversed(includelines):
                                    lines.append(" "*(current_indent-includeindent) + includeline)
                                    numbers.append(i)
                            skip = True
                            continue

                        new_tag = QqTag(tag, [])

                        current_tag.append_line(self.unescape_line("".join(chunk)))
                        chunk = []

                        current_tag.append_child(new_tag)

                        stack.append(StackElement(new_tag, indent))

                        if len(lines) > 0 and self.get_indent(lines[-1]) > indent:
                            current_indent = self.get_indent(lines[-1])
                            tag_indent = current_indent
                        else:
                            tag_indent = self.get_indent(line) + 4
                            # virtual tag indent

                        rest = lin[m.end():]
                        restlines = [" "*tag_indent + l.lstrip() for l in self.split_line_by_tags(rest)
                                     if l.strip() != ""]
                        if restlines:
                            current_indent = tag_indent
                        for restline in reversed(restlines):
                            lines.append(restline)
                            numbers.append(i)

                        # the rest of line is added to lines, so we may continue -- they will be processed automatically
                        continue

            # Process inline tags

            inlines = re.finditer(self.command_regex +
                                  r'(?P<tag>' + self.tag_regex + ')' +
                                  r'(?P<bracket>[\{\[])' +
                                  r"|[\{\[\]\}]", line)


            # inline tags or brackets

            cursor = current_indent

            for m in inlines:
                if stack[-1].indent is None:
                    if m.group(0) == stack[-1].bracket:
                        stack[-1].bracket_counter += 1
                    elif m.group(0) == {'{': '}', '[': ']'}[stack[-1].bracket]:
                        # closing bracket corresponding to current open tag
                        stack[-1].bracket_counter -= 1
                        if stack[-1].bracket_counter == 0:
                            # close current inline tag

                            r"""
                            \blocktag
                                Some \inlinetag[started
                                and here \otherinlinetag{continued}
                                here \otherblocktag started
                                and here two lines | separated from each other
                                and that's all for inlinetag] we continue

                            --->

                            \blocktag
                                Some
                                    \inlinetag
                                        started
                                        and here
                                        \otherinlinetag
                                            continued
                                        here
                                        \otherblocktag
                                            started and here two lines
                                        <separator>
                                        separated from each other
                            """
                            chunk.append(line[cursor: m.start()])
                            chunknumbers.append(i)
                            if stack[-1].bracket == '{':

                                current_tag.append_line(self.unescape_line("".join(chunk)))
                                chunk = []

                                cursor = m.end()

                                self.pop_stack()
                                current_tag = stack[-1].tag
                            else:
                                newline = line[m.end():]
                                if newline and newline[0] == ' ':
                                    newline = self.escape_line("\\ ") + newline[1:]
                                lines.append(" "*current_indent + newline)
                                numbers.append(i)
                                # push the rest of line to lines to process them later

                                splitted_chunk = [" "*(current_indent+4) + l.lstrip()
                                                  for l in self.split_line_by_tags("".join(chunk))
                                                  if l.strip() != ""]
                                if splitted_chunk:
                                    for newline in reversed(splitted_chunk):
                                        lines.append(newline)
                                        numbers.append(i)
                                        # TODO: numbers will refer to the number of line where tag is closed
                                    stack[-1].bracket = None
                                    stack[-1].indent = current_indent
                                    current_indent += 4
                                else:
                                    self.pop_stack()
                                    current_tag = stack[-1].tag

                                chunk = []
                                skip = True
                                # this is done to skip the rest of line at the end of while

                                break

                inline_tag = m.group('tag')
                if inline_tag is not None and stack[-1].bracket != '[':
                    if inline_tag in self.allowed_inline_tags:

                        chunk.append(line[cursor: m.start()])
                        chunknumbers.append(i)
                        current_tag.append_line(self.unescape_line("".join(chunk)))
                        chunk = []

                        new_tag = QqTag(inline_tag, [])

                        current_tag.append_child(new_tag)
                        stack.append(StackElement(new_tag, indent=None,
                                                  bracket=m.group('bracket'),
                                                  bracket_counter=1))
                        current_tag = new_tag
                        cursor = m.end()
                    else:
                        if stack[-1].indent is None and m.group('bracket') == stack[-1].bracket:
                            # Process case of non-allowed tag with bracket for correct brackets counting
                            stack[-1].bracket_counter += 1

            if not skip:
                # cursor is None if special inline tag is closed and nothing has to be done here
                # Append the rest of line to current tag
                chunk.append(line[cursor:])
                chunknumbers.append(i)

        # append final lines to tag
        current_tag.append_line(self.unescape_line("".join(chunk)))

        tree.process_separator_recursively(self.separator)

        return tree