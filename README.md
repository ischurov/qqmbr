# qqmbr
## Fresh documentation system

**qqmbr** is a documentation system intended to be extremely simple and extremely extensible. 
It was written to allow writing rich content that can be compiled into different formats.
One source, multiple media: HTML, XML, LaTeX, PDF, eBooks, any other. Look below to see it in action.

### Highlights
**qqmbr** is based on **qqDoc** markup. It has the following features:

- Clean syntax. On micro-level, we use well-known [Markdown syntax](https://daringfireball.net/projects/markdown/)
So all that **bolds** and _italics_ stuff is familiar.
On macro-level we have tags. They are auto-closing: just unindent the line (like in Python). 
And also we have so-called inline tags, e.g. for ref's and links. And that's all about the syntax.
- Extensibility. Tags can be anything. LaTeX-style environments like *Theorem 1* or *Lemma 2* or *Definition 3*.
Figures with captions. Some complicated data that can be used to render something interactive. Everything is tag.
- Simple parsing. The source is parsed into a kind of [s-expression](https://en.wikipedia.org/wiki/S-expression) 
which can be transformed into any other format.

### View in action
You can look at my Lecture Notes on ODE source (see e.g. [this qqDoc source](https://github.com/ischurov/odebook/blob/master/chapter03.qq) and 
[its HTML render](http://math-info.hse.ru/f/2015-16/nes-ode/chapter03.html), in Russian) or at the [code sample](#code_sample) below.

### Inspiration
**qqmbr** and **qqDoc** were inspired by various projects and conceptions:

- [Python](https://www.python.org/) for the importance of indents (and it is written in Python too!);
- [YAML](http://www.yaml.org/) for indent-based markup language;
- [DocOnce](https://github.com/hplgit/doconce) for 'one source to any media' approach and some ideas on realization;
- [S-expressions](https://en.wikipedia.org/wiki/S-expression) for simplicity (why they have attributes in XML?)

### Current status
Currently, we have full-featured **qqDoc** parser and basic *qqHTML* formatter. The following features are on the to-do list:

- setuptools install and PyPI distribution.
- *qqLaTeX* formatter.
- more features in *qqHTML*:
    - snippets and glossary (like [here](http://math-info.hse.ru/odebook/._thebook002.html) (hover on «задача Коши» link).
    - more math environments (`gather`, `align` and so on);
    - quizzes, like in DocOnce (see e.g. [here](http://math-info.hse.ru/odebook/._thebook001.html), look for «Контрольный вопрос»);
    - admonitions (boxes for warning, notice, question, etc.), like in DocOnce.

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

