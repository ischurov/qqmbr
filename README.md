# qqmbr
## Fresh documentation system

### Intro

    \h1 Intro to qqmbr
    
    \h2 Fresh documentation system
    
    **qqmbr** is a documentation system intended to be extremely simple and extremely extensible. 
    It was written to allow writing rich content that can be compiled into different formats.
    One source, multiple media: HTML, XML, LaTeX, PDF, eBooks, any other. Look below to see it in action.
    
    \h3 This is nice level-3 header
    
    Some paragraph text. See also \ref{sec:another} (reference to different header).
    
    There are LaTeX formulas here:
    
    \eq
        x^2 + y^2 = z^2
    
    `\eq` is a qqtag. It is better than tag, because it is auto-closing (look at the indent, like Python).
    
    Here is formula with the label:
    
    \equation | label: eq:Fermat
        x^n + y^n = z^n, \quad n>2
        
    Several formulas with labels:
    
    \gather
        \item | label: eq:2x2
            2\times 2 = 4
        \item | label: eq:3x3
            3\times 3 = 9
    
    We can reference formula \eqref{eq:Fermat} and \eqref{eq:2x2} just like we referenced header before.
    
    \h3 Another level-3 header | label: sec:another
    
    Here is the header we referenced.
    
    \h3 More interesting content
    
    \figure
        \source http://example.com/somefig.png
        \caption Some figure
        \width 500px
    
    \question
        Do you like it?
        \quiz
            \choice | correct: false
                No.
                \comment You didn't even try!
            \choice | correct: true
                Yes, i like it very much!
                \comment And do I!


### Highlights

Why yet another one documentation system? Why yet another one markup? We already have lots of them!
Maybe. I feel I need this. And I wrote it. This is why:

- Clean syntax. On micro-level, we use well-known [Markdown syntax](https://daringfireball.net/projects/markdown/)
So all that **bolds** and _italics_ stuff is familiar.
On macro-level we have tags. They are auto-closing: just unindent the line (like in Python). 
And also we have so-called inline tags, e.g. for ref's and links (see above). And that's all about the syntax.
- Extensibility. Tags can be anything. LaTeX-style environments like *Theorem 1* or *Lemma 2* or *Definition 3*.
Figures with captions. Some complicated data that can be used to render something interactive. Everything is tag.
- Simple parsing. The source is parsed into a kind of [s-expression](https://en.wikipedia.org/wiki/S-expression) 
which can be transformed into any other format.
