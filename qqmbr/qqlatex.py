# some comment

from qqmbr.ml import QqTag

class QqLaTeXFormatter(object):

    def __init__(self, root: QqTag=None, allowed_tags=None):
        self.root = root
        self.allowed_tags = allowed_tags or set()
        self.enumerateable_envs = {name: name.capitalize() for name in ['remark', 'theorem', 'example', 'exercise',
                                                                    'definition', 'proposition', 'lemma',
                                                                        'question', 'corollary']}
        self.tag_to_latex = {'h1':'section', 'h2':'subsection',
                             'h3':'subsubsection', 'h4':'paragraph'}

        self.enumerateable_envs = {name: name.capitalize() for name
                                   in ['remark', 'theorem', 'example',
                                       'exercise', 'definition',
                                       'proposition', 'lemma', 'question',
                                       'corollary']}


    def uses_tags(self):
        members = inspect.getmembers(self, predicate=inspect.ismethod)
        handles = [member for member in members if member[0].startswith("handle_") or member[0] == 'preprocess']
        alltags = set([])
        for handle in handles:
            if handle[0].startswith("handle_"):
                alltags.add(handle[0][len("handle_"):])
            doc = handle[1].__doc__
            if not doc:
                continue
            for line in doc.splitlines():
                m = re.search(r"Uses tags:(.+)", line)
                if m:
                    tags = m.group(1).split(",")
                    tags = [tag.strip() for tag in tags]
                    alltags.update(tags)
        alltags.update(self.enumerateable_envs.keys())
        return alltags

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
        handlers_available = ['h1', 'h2', 'eq', 'paragraph']
        name = tag.name
        default_handler = 'handle_dummy'
        if name in handlers_available:
            return getattr(self, 'handle_'+name)(tag)
        elif hasattr(self, default_handler):
            return getattr(self, default_handler)(tag)
        else:
            return ""

    def handle_dummy(self, tag):
        # The original 'handle' function we wrote on December 1 (almost)
        """
        Parameters
        ----------
        tag: QqTag

        Returns "\begin{tag name}
                    tag content
                 \end{tag name}
        -------

        """
        name = tag.name
        return """
\\begin{{{name}}}
    {content}
\end{{{name}}}
""".format(name=self.name, content=self.format(tag))

    def handle_h1(self, tag):  # h1 = chapter
        """
        Parameters
        ----------
        tag: QqTag

        Returns "\begin{chapter}
                    tag content
                 \end{chapter}
        -------

        """
        return """
\\begin{{{name}}}
    {content}
\end{{{name}}}
""".format(name="chapter", content=self.format(tag))

    def handle_h2(self, tag):  # h2 = section
        """
        Parameters
        ----------
        tag: QqTag

        Returns "\begin{section}
                    tag content
                 \end{section}
        -------

        """
        name = tag.name
        return """
\\begin{{{name}}}
    {content}
\end{{{name}}}
""".format(name=self.tag_to_latex[name], content=self.format(tag))

    def handle_paragraph(self, tag):  #paragraph = subsection
        """
        Parameters
        ----------
        tag: QqTag

        Returns "\begin{subsection}
                    tag content
                 \end{subsection}
        -------

        """
        name = tag.name
        print(tag)
        if tag.find('label'):  #this does not work, but have a look
            print(tag)
            label = tag.split('label ')[-1]
            return """
\\begin{{{name}}} \label{{{label}}}
    {content}
\end{{{name}}}
""".format(name="subsection", content=self.format(tag), label=label)
        else:
            return """
\\begin{{{name}}}
    {content}
\end{{{name}}}
""".format(name=self.tag_to_latex[name], content=self.format(tag))

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