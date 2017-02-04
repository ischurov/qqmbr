import inspect
import re
from qqmbr.ml import QqTag
from qqmbr.formatter import QqFormatter

class QqLaTeXFormatter(QqFormatter):

    def __init__(self, root: QqTag=None, allowed_tags=None):
        self.root = root
        self.allowed_tags = allowed_tags or set()
        self.enumerateable_envs = {name: name.capitalize() for name in ['remark', 'theorem', 'example', 'exercise',
                                                                    'definition', 'proposition', 'lemma',
                                                                        'question', 'corollary']}
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
        default_handler = 'handle_simple'
        if name in self.enumerateable_envs:
            return getattr(self, 'handle_begin_end')(tag)
        elif name == 'eq':
            return getattr(self, 'handle_eq')(tag)
        elif hasattr(self, default_handler):
            return getattr(self, default_handler)(tag)
        else:
            return ""

    def handle_simple(self, tag):
        """
        Uses tags: h1, h2, h3, h4, paragraph
        :param tag:
        :return:
            \{tag name}
            tag content
        """
        return """
\{{{name}}} \{{{label}}}
{content}
""".format(name=self.tag_to_latex[tag.name], content=self.format(tag), label = tag.find('label'))

    def handle_begin_end(self, tag):
        """
        Uses tags: remark, theorem, example, exercise, definition, proposition, lemma, question, corollary
        :param tag:
        :return:
            \begin{tag name}
            tag content
            \end{tag name}
        """
        return """
\\begin{{{name}}}
{content}
\end{{{name}}}
""".format(name=tag.name, content=self.format(tag))

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