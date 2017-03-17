import inspect
import re
from qqmbr.ml import QqTag
from qqmbr.formatter import QqFormatter

class QqLaTeXFormatter(QqFormatter):

    def __init__(self, root: QqTag=None, allowed_tags=None):
        self.root = root
        self.allowed_tags = allowed_tags or set()
        self.enumerable_envs = {name: name.capitalize() for name in ['remark', 'theorem', 'example', 'exercise',
                                                                    'definition', 'proposition', 'lemma',
                                                                        'question', 'corollary']}
        self.simple_tags = ['h1', 'h2', 'h3', 'h4', 'paragraph']
        self.tag_to_latex = {'h1':'section', 'h2':'subsection',
                                 'h3':'subsubsection', 'h4':'paragraph',
                                 'paragraph':'paragraph'}

        super().__init__()

    def format(self, content) -> str:
        """

        :param content: could be QqTag or any iterable of QqTags
        :param blanks_to_pars: use blanks_to_pars (True or False)
        :return: str: text of tag
        """
        if content is None:
            return ""

        out = []

        for child in content:
            if isinstance(child, str):
                out.append(child)
            else:
                out.append(self.handle(child))
        return "".join(out)

    def handle(self, tag):
        name = tag.name
        default_handler = 'handle_empty'
        if name in self.enumerable_envs:
            return self.handle_enumerables(tag)
        elif name in self.simple_tags:
            return self.handle_simple(tag)
        elif name == 'eq':
            return self.handle_eq(tag)
        elif hasattr(self, default_handler):
            return getattr(self, default_handler)(tag) # I still need gettatr here, right?
        else:
            return ""

    def handle_empty(self, tag):
        """
        Uses tags: label
        :param tag:
        :return: tag:
        """
        return ""

    def handle_simple(self, tag):
        """
        Uses tags: h1, h2, h3, h4, paragraph
        :param tag:
        :return:
            \{tag name}
            tag content
        """
        label_string = ''
        if tag.exists("label"):
            label_string = '\label{{{label}}}'.format(label=tag.find('label')[0])
        caption_string = ''
        if len(tag)>0:
            caption_string = '{{{caption}}}'.format(caption = tag[0])
        return """
\{name}{caption} {label}
{content}
""".format(name=self.tag_to_latex[tag.name], content=self.format(tag),
           label = label_string, caption = caption_string)

    def handle_enumerables(self, tag):
        """
        Uses tags: remark, theorem, example, exercise, definition, proposition, lemma, question, corollary
        :param tag:
        :return:
            \begin{tag name}
            tag content
            \end{tag name}
        """
        label_string = ''
        if tag.exists("label"):
            label_string = '\label{{{label}}}'.format(label=tag.find('label')[0])
        return """
\\begin{{{name}}} {label}
{content}
\end{{{name}}}
""".format(name=tag.name, content=self.format(tag), label = label_string)

    def handle_eq(self, tag: QqTag) -> str:
        """
        eq tag corresponds to \[ \] or $$ $$ display formula without number.

        Example:

        \eq
            x^2 + y^2 = z^2

        :param tag:
        :return:
            $$x^2 + y^2 = z^2$$
        """
        return """
$${content}$$
""".format(content=self.format(tag))

    def do_format(self):
        return self.format(self.root)