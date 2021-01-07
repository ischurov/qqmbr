# qqmbr
## Mathematical layout for web and paper

**qqmbr** is a publishing engine for mathematical texts that aims on different media: web, mobile and paper.

### Highlights

- Clean syntax, based on [indentml](https://github.com/ischurov/indentml) markup. It's a mixture of Python-style indent-based blocks and LaTeX-style commands beginning with backslash, see code samples below.
- Excellent equation support on web and mobile, thanks to MathJax.
- All what you need to structure your text: different levels of headers, environments (*theorem*, *lemma* and so on).
- References by labels.
- Preview of equations and definitions on hover (a.k.a. *snippets*, see example [here](http://ode.mathbook.info/chapter/label/chap:2:auto/#label_sec_2_euler), look for «Контрольный вопрос»)).
- Interactive quizes, (see example [here](http://ode.mathbook.info/chapter/label/chap:notion_of_ODE/#label_par_1_Cauchy_problem)).
- Programmatically generated images embedding (matplotlib and plotly).

### View in action
You can look at my Lecture Notes on ODE sources (see e.g. [this qqmbr source](https://github.com/ischurov/odebook/blob/master/chapter03.qq) and 
[its HTML render](http://math-info.hse.ru/f/2015-16/nes-ode/chapter03.html), in Russian) or at the [code sample](#code-sample) below.

You can also play with limited subset of **qqmbr** features in [live demo](http://math-info.hse.ru/qqmathpreview).

### Inspiration
**qqmbr** was inspired by various projects and conceptions:

- [TeX](https://tug.org/) and [LaTeX](https://www.latex-project.org/) for math and backslashes.
- [Python](https://www.python.org/) for the importance of indents (and **qqmbr** is written in Python!);
- [YAML](http://www.yaml.org/) for indent-based markup language;
- [DocOnce](https://github.com/hplgit/doconce) for *one source to any media* approach and some ideas on realization;
- [S-expressions](https://en.wikipedia.org/wiki/S-expression) for simplicity (why they have attributes in XML?).

### TODO
The following features are on the to-do list:

- **QqLaTeXFormatter** that converts *qqmbr* source code to *LaTeX*.
- more layour features:
    - more math environments (`gather`, `multline` and so on);
    - admonitions (boxes for warning, notice, question, etc.), like in DocOnce;

You are welcome to participate with pull requests and issue-reporting.

### Code sample

This is an example of **qqmbr** markup. See [live demo](http://mathbook.info/qqmathpreview).

    \chapter Euler's formula
    \section Complex numbers \label sec:comlex
    
    One can introduce \em{complex numbers} by considering so-called \em{imaginary unit} $i$, such that:
    \equation \label eq:i
        i^2 = -1.
    \definition
        \emph{Complex number} is a number of a form $x+iy$, where $x, y \in \mathbb R$.
    
    \section Exponent of complex number \label sec:exp
    \theorem \label thm:1
        Let $x$ be real number. Then
        \equation \label eq:main
            e^{ix} = \cos x+i\sin x.
    \proof
        Let us recall series for exponent, sine and cosine:
        \align
            \item \label eq:series-exp
                e^z &= 1 + z + \frac{z^2}{2} + \frac{z^3}{3!} + \ldots = \sum_{k=0}^\infty \frac{z^k}{k!}
            \item \label eq:series-sin
                \sin z &= z - \frac{z^3}{3!} + \frac{z^5}{5!} - \frac{z^7}{7!} + \ldots
            \item \label eq:series-cos
                \cos z &= 1 - \frac{z^2}{2} +\frac{z^4}{4!} - \frac{z^6}{6!} + \ldots
        It follows from \ref{eq:i} that
        \eq
            i^k=\begin{cases}
                1 & \text{for } k = 4m\\\\
                i & \text{for } k = 4m+1\\\\
                -1 & \text{for } k = 4m+2\\\\
                -i & \text{for } k = 4m+3
                \end{cases}
        Let us put $z=ix$ into \ref{eq:series-exp}. For even $k$, $(ix)^k$ is real and for odd $k$ it is imaginary. Moreover, the sign alternates when one pass to the next term. It follows immediately that the real part of \ref{eq:series-exp} is equal to \ref{eq:series-sin} and the imaginary part is equal to \ref{eq:series-cos} with substitution $z=ix$.
    
        This finished the proof of \ref[Euler's formula\nonumber][thm:1].
    
    \chapter Corollary
    
    It follows from \ref[Theorem][thm:1] from \ref[Section][sec:exp] that
    \eq
        \sin x = \frac{e^{ix}-e^{-ix}}{2i}.
    Therefore,
    \align
        \item \nonumber
            \sin 2x &= \frac{e^{2ix}-e^{-2ix}}{2i} = \frac{1}{2i}((e^{ix})^2-(e^{-ix})^2)=
        \item \nonumber
            &\frac{1}{2i}(e^{ix}-e^{-ix})(e^{ix}+e^{-ix})=2\sin x \cos x.
    
    \question
        Express $\cos x$ in terms of exponents. (Click on pencil to check the correct answer.)
        \quiz
            \choice
                $(e^{ix}+e^{-ix})/(2i)$
                \comment
                    No, this is complex number!
            \choice \correct
                $(e^{ix}+e^{-ix})/2$
                \comment
                    Yes! That's right!
            \choice
                $(e^{ix}-e^{-ix}))/(2)$
                \comment
                    No, that's $-i\sin x$.
    
    \exercise
        Express $\cos 2x$ in terms of $\sin x$ and $\cos x$.

