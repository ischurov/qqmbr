from qqmbr.qqdoc import QqParser, QqTag
from yattag import Doc
import mistune
import re

def mk_safe_css_ident(s):
    # see http://stackoverflow.com/a/449000/3025981 for details
    s = re.sub("[^a-zA-Z\d_-]", "_", s)
    if re.match("([^a-zA-Z]+)", s):
        m = re.match("([^a-zA-Z]+)", s)
        first = m.group(1)
        s = s[len(first):] + "__" + first
    return s


class Counter():
    """
    Very simple class that support latex-style counters with subcounters.
    For example, if new section begins, the enumeration of subsections resets.
    That's all.
    """

    def __init__(self):
        self.value = 0
        self.child = None
        self.parent = None

    def reset(self):
        self.value = 0
        if self.child:
            self.child.reset()

    def increase(self):
        self.value += 1
        if self.child:
            self.child.reset()

    def spawn_child(self):
        self.child = Counter()
        self.child.parent = self
        return self.child

    def __str__(self):
        my_str = str(self.value)
        if self.parent:
            my_str = str(self.parent) + "." + my_str
        return my_str

class QqHTMLFormatter(object):

    def __init__(self, root: QqTag):
        self.tag_handlers = {
            'h1': self.handle_h,
            'h2': self.handle_h,
            'h3': self.handle_h,
            'h4': self.handle_h,
            'eq': self.handle_eq,
            'equation': self.handle_equation,
            'ref': self.handle_ref,
            'eqref': self.handle_eqref
        }
        self.ref2number = {}
        self.ref2title = {}
        self.root = root
        self.counters = {}

        self.counters['h1'] = Counter()
        self.counters['h2'] = self.counters['h1'].spawn_child()
        self.counters['h3'] = self.counters['h2'].spawn_child()
        self.counters['h4'] = self.counters['h3'].spawn_child()

        self.counters['equation'] = self.counters['h1'].spawn_child()

        mistune_renderer = mistune.Renderer(escape=False)
        self.markdown = mistune.Markdown(renderer=mistune_renderer)


    def handle(self, tag):
        if tag.name in self.tag_handlers:
            return self.tag_handlers[tag.name](tag)
        else:
            return ""

    def label2id(self, label):
        return "label_" + mk_safe_css_ident(label.strip())

    def format(self, tag: QqTag, markdown = False):
        out = []

        for child in tag.children:
            if isinstance(child, str):
                if markdown:

                    # Preserve whitespaces (markdown will remove it)

                    m = re.match(r"(\s*).*\S(\s*)", child)
                    if m:
                        pre, post = m.groups()
                    else:
                        pre = post = ""

                    chunk = self.markdown(child)
                    m = re.match(r"<p>(.+)</p>$", chunk)
                    if m:
                        chunk = m.group(1)
                    chunk = pre + chunk + post
                    out.append(chunk)
                else:
                    out.append(child)
            else:
                out.append(self.handle(child))
        return "".join(out)

    def handle_h(self, tag):
        doc, html, text = Doc().tagtext()
        with html(tag.name):
            if tag.find("label"):
                doc.attr(id=self.label2id(tag._label.value))
            elif tag.find("number"):
                doc.attr(id=self.label2id(tag.name+"_number_"+str(tag._number.value)))
            if tag.find("number"):
                with html("span", klass="section__number"):
                    text(tag._number.value + ". ")
            text(self.format(tag))
        return doc.getvalue()


    def handle_eq(self, tag):
        doc, html, text = Doc().tagtext()
        with html("div", klass="latex_eq"):
            text("\\[\n")
            text(self.format(tag))
            text("\\]\n")
        return doc.getvalue()

    def handle_equation(self, tag):
        doc, html, text = Doc().tagtext()
        with html("div", klass="latex_equation"):
            text("\\[\n")
            text("\\begin{equation}\n")
            if tag.find('number'):
                text("\\tag{{{}}}\n".format(tag._number.value))
            if tag.find('label'):
                doc.attr(id=self.label2id(tag._label.value))
            text(self.format(tag))
            text("\\end{equation}\n")
            text("\\]\n")
        return doc.getvalue()

    def handle_ref(self, tag):
        doc, html, text = Doc().tagtext()
        number = self.ref2number.get(tag.value.strip(), "???")
        ref = tag.value.strip()
        with html("span", klass="ref"):
            with html("a", klass="a-ref", href="#"+self.label2id(ref),
                      title=self.ref2title.get(ref,"")):
                text(number)
        return doc.getvalue()

    def handle_eqref(self, tag):
        doc, html, text = Doc().tagtext()
        number = self.ref2number.get(tag.value, "???")
        with html("span", klass="ref"):
            with html("a", klass="a-ref", href="#"+self.label2id(tag.value.strip())):
                text("("+number+")")
        return doc.getvalue()

    def preprocess(self):
        for tag in self.root.children:
            if isinstance(tag, QqTag) and tag.name in self.counters:
                counter = self.counters[tag.name]
                counter.increase()
                tag.append_child(QqTag({'number': str(counter)}))
                if tag.find('label'):
                    label = tag._label.value.strip()
                    self.ref2number[label] = str(counter)
                    self.ref2title[label] = tag.text_content

    def do_format(self):
        self.preprocess()
        return self.format(self.root, markdown=True)
