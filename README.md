# qqmbr
## Fresh documentation system

**qqmbr** is a documentation system intended to be extremely simple and extremely extensible. 
It was written to allow writing rich content that can be compiled into different formats.
One source, multiple media: HTML, XML, LaTeX, PDF, eBooks, any other. Look below to see it in action.

### Highlights
**qqmbr** is based on **qqDoc** markup. It has the following features:

- Clean syntax. On micro-level, we use well-known [Markdown syntax](https://daringfireball.net/projects/markdown/).
So all that **bolds** and _italics_ stuff is familiar. Formula formatting is LaTeX (handled by [MathJax](http://mathjax.org/) in HTML).
On macro-level we have tags. They are auto-closing: just unindent the line (like in Python). 
And also we have so-called inline tags, e.g. for ref's (again very LaTeX-like: `\eqref{eq:main}`). 
That's almost all: see *complete* [qqDoc syntax description](#qqdoc-syntax) below for details.
- Extensibility. Tags can be anything. LaTeX-style environments like *Theorem 1* or *Lemma 2* or *Definition 3*.
Figures with captions. Some complicated data that can be used to render something interactive. Everything is a tag.
- Simple parsing. The source is parsed into a kind of [s-expression](https://en.wikipedia.org/wiki/S-expression) 
which can be transformed into any other format.

### View in action
You can look at my Lecture Notes on ODE sources (see e.g. [this qqDoc source](https://github.com/ischurov/odebook/blob/master/chapter03.qq) and 
[its HTML render](http://math-info.hse.ru/f/2015-16/nes-ode/chapter03.html), in Russian) or at the [code sample](#code-sample) below.

### Inspiration
**qqmbr** and **qqDoc** were inspired by various projects and conceptions:

- [TeX](https://tug.org/) and [LaTeX](https://www.latex-project.org/) for math and backslashes.
- [Python](https://www.python.org/) for the importance of indents (and **qqmbr** is written in Python!);
- [YAML](http://www.yaml.org/) for indent-based markup language;
- [DocOnce](https://github.com/hplgit/doconce) for *one source to any media* approach and some ideas on realization;
- [S-expressions](https://en.wikipedia.org/wiki/S-expression) for simplicity (why they have attributes in XML?).

### Current status
Currently, we have full-featured **qqDoc** parser and basic *qqHTML* formatter. The following features are on the to-do list:

- setuptools install and PyPI distribution.
- *qqLaTeX* formatter.
- more features in *qqHTML*:
    - snippets and glossary (like [here](http://math-info.hse.ru/odebook/._thebook002.html) (hover on «задача Коши» link).
    - more math environments (`gather`, `align` and so on);
    - quizzes, like in DocOnce (see e.g. [here](http://math-info.hse.ru/odebook/._thebook001.html), look for «Контрольный вопрос»);
    - admonitions (boxes for warning, notice, question, etc.), like in DocOnce;
    - many others.

You are welcome to participate with pull requests and issue-reporting.

### Code sample

This is an example of **qqmbr** markup (subset of **qqDoc** markup).

    \h1 Intro to qqmbr
    
    \## Fresh documentation system
    
    **qqmbr** is a documentation system intended to be extremely simple and extremely extensible. 
    It was written to allow writing rich content that can be compiled into different formats.
    One source, multiple media: HTML, XML, LaTeX, PDF, eBooks, any other. Look below to see it in action.
    
    \### This is nice level-3 header
    
    Some paragraph text. See also \ref{sec:another} (reference to different header).
    
    There are LaTeX formulas here:
    
    \eq
        x^2 + y^2 = z^2
    
    `\eq` is a qqtag. It is better than tag, because it is auto-closing (look at the indent, like Python).
    
    Here is formula with the label:
    
    \equation \label eq:Fermat
        x^n + y^n = z^n, \quad n>2
        
    Several formulas with labels:
    
    \gather
        \- \label eq:2x2
            2\times 2 = 4
        \- \label eq:3x3
            3\times 3 = 9
    
    We can reference formula \eqref{eq:Fermat} and \eqref{eq:2x2} just like we referenced header before.
    
    \h3 Another level-3 header | \label sec:another
    
    Here is the header we referenced.
    
    \h3 More interesting content
    
    \figure
        \source http://example.com/somefig.png
        \caption Some figure
        \width 500px
    
    \question
        Do you like qqmbr?
        \quiz
            \choice \correct false
                No.
                \comment You didn't even try!
            \choice \correct true
                Yes, i like it very much!
                \comment And so do I!


### qqDoc Syntax
**qqDoc** is a general-purpose markup (or *metalanguage*, like XML), while **qqmbr** is a subset of **qqDoc** markup (or **qqDoc**-based markup language) 
used to produce documents in HTML and LaTeX.

Internal representation of **qqDoc** is an [s-expression](https://en.wikipedia.org/wiki/S-expression)-like tree structure. 
It can be also represented as attribute-free XML.

The following rules describe complete **qqDoc** syntax:

#### Special characters
The following characters have special meaning in **qqDoc**:

1. **Tag beginning character.** This character is used to mark the beginning of any tag. By default, it is backslash `\` 
(like in LaTeX), but can be configured to any other character. If you need to enter this character literally, you have 
to escape it with the same character (like `\\`). You can also escape other special characters listed below with *tag beginning character*.
2. **Separator character** is used to separate the rest of line which contains *block tag* (see below). By default it is pipe `|`.
3. Opening and closing brackets: `{`, `}`, and `[`, `]`, used to indicate the content that belongs to *inline tags*, see below.
4. Tabs are forbidden at the beginning of the line in **qqDoc** (just like in YAML).

#### Block tags
Block tags are typed at the beginning of the line, after several spaces that mark *indent* of a tag.  
Block tag starts with *tag beginning character* and ends with the whitespace or newline character. All the lines below the block tag
belongs to this tag while their indent is greater than tag's indent. When indent decreases, tag is closed. E.g.

    \tag
        Hello
        \othertag
            I'm qqDoc
        How are you?
    I'm fine
    
will be translated into the following XML tree:

    <tag>Hello
    <othertag>
    I'm qqDoc
    </othertag>
    How are you?
    </tag>
    I'm fine

The rest of line where block tag begins will be attached to that tag either, but it will be handled a bit differently
if it contains a *separator character*. If there is such character, then the line is splitted by this character and all parts
are attached to the tag as if they were on different lines. For example:

    \image \src http://example.com | \width 100%
        Some image

Is equivalent to
    
    \image
        \src
            http://example.com
        \width
            100%
    Some image

And renders to the following XML:

    <image>
    <src>
    http://example.com
    </src>
    <width>
    100%
    </width>
    Some image
    </image>
    
This allows to add attribute-like subtags in a compact way.

Note that if several tags are on the first line without separator character, they will be nested:

    \tag1 \tag2 \tag3 test
    
Is equivalent to

    \tag1
        \tag2
            \tag3
                test
                
Tag name doesn't necessary should be valid Python identifier, e.g. one can introduce markdown-style header tags like

    \### I'm header of 3'd level
    \#### And I'm header of 4'th level

#### Inline tags
Inline tags are started with *tag beginning character* and ended by bracket: `{` or `[`. Curve bracket is 
the default, square brackets are reserved to allow special handlers of some tags in future. Tag contents is everything
between its opening bracket and corresponding closing bracket. Brackets (of the same kind) inside the tag should be either
balanced or escaped.

For example,

    This is \tag{with some {brackets} inside}
    
is valid markup: the contents of tag `tag` will be `with some {brackets inside}`.

Inline tags may be extended through several lines, but it is forbidden to open or close block tags inside inline tag.

There is no difference between block tags and inline tags in terms of resulting tree.

#### Allowed tags
Only those tags are processed that are explicitly *allowed*. There are two sets defined: allowed block tags and allowed inline tags.
The sequences that look like tags but are not in the appropriate set is considered as simple text.

#### Indents and whitespaces
Indent of the first line after the block tag is a *base indent* of this tag. All lines that belong to tag will be stripped 
from the left by the number of leading whitespaces that corresponds to the base indent. The rest of whitespaces will be preserved.

For example:

    \pythoncode
        for i in range(1, 10):
            print(i)

Here the contents of `pythoncode` tag is `"for i in range(1, 10):\n    print(i)` (note four whitespaces before `print`).

If a line has an indent that is less than *base indent*, it MUST be equal to the indent of one of open block tags. Than 
all the tags up to that one (including that one) will be closed.

For example, the following is forbidden:

    \code
        some string with indent 4
      some string with indent 2

It is possible to use any indent values but multiples of 4 are recommended (like [PEP-8](https://www.python.org/dev/peps/pep-0008/)).
