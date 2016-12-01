from qqmbr.ml import QqTag

class QqXMLFormatter(object):

    def __init__(self, root: QqTag=None, allowed_tags=None):
        self.root = root
        self.allowed_tags = allowed_tags or set()

    def uses_tags(self):
        return self.allowed_tags

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
        """
        Parameters
        ----------
        tag: QqTag

        Returns "<tag name>tag content</tag name>"
        -------

        """
        name = tag.name
        return "<{name}>{content}</{name}>".format(
            name=name,
            content = self.format(tag)
        )

    def do_format(self):
        return self.format(self.root)
