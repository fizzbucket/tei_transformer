import os

def languages_used():
    """Return dictionary of languages.
    This maps the TEI codes for languages used in your project to the forms used in latex, defined in the preamble.
    """
    return {
        'it': 'italian',
        'de': 'german',
        'la': 'latin',
        'fr': 'french',
        'gr': 'greek',
    }

def unicode_to_latex():
    """Return dictionary mapping unicode characters to latex codes."""
    return {
        #u"\u0024": "\\textdollar ",
        u"\u0025": "\\%",
        " &amp; ": " \\& ",
        u"\u00A2": "\\textcent ",
        u"\u00A3": "\\textsterling ",
        u"\u00A4": "\\textcurrency ",
        u"\u00A5": "\\textyen ",
        u"\u00A9": "\\textcopyright ",
        u"\u00AB": "\\guillemotleft ",
        u"\u00B0": "\\textdegree ",
        u"\u00BA": "\\textordmasculine ",
        u"\u00BB": "\\guillemotright{} ",
        u"\u00BC": "\\textonequarter ",
        u"\u00BD": "\\textonehalf ",
        u"\u00BE": "\\textthreequarters ",
        u"\u00BF": "\\textquestiondown ",
        u"\u00D7": "\\texttimes ",
        u"\u2122": "\\texttrademark ",
        u"\u2153": "\\textfrac{1}{3}",
        u"\u2154": "\\textfrac{2}{3}",
        u"\u2155": "\\textfrac{1}{5}",
        u"\u2156": "\\textfrac{2}{5}",
        u"\u2157": "\\textfrac{3}{5}",
        u"\u2158": "\\textfrac{4}{5}",
        u"\u2159": "\\textfrac{1}{6}",
        u"\u215A": "\\textfrac{5}{6}",
        u"\u215B": "\\textfrac{1}{8}",
        u"\u215C": "\\textfrac{3}{8}",
        u"\u215D": "\\textfrac{5}{8}",
        u"\u215E": "\\textfrac{7}{8}",
        u"\u2190": "$\\leftarrow $",
        u"\u2191": "$\\uparrow $",
        u"\u2192": "$\\rightarrow $",
        u"\u2193": "$\\downarrow $",
        u"\u00F7": "$\\div $",
        #u"\u007C": "\\textbar{}",
        '...': '\ldots{}',
    }

def custom_string_replacements():
    """Return a dictionary mapping strings to be replaced in the latex file.
    The normal usage of this is to handle things like problematic hyphenation or spacing.
    These will be replaced after parsing is complete."""
    return {
        'i.e. ': 'i.e.\ ',
        'e.g. ': 'e.g.\ ',
        ' v. ': ' v.\ ',
        ' w. ': ' w.\ ',
        ' wh. ': ' wh.\ ',
        'MG. ': 'MG.\@ ',
        'HQ. ': 'HQ.\@ ',
        'YMCA. ': 'YMCA.\@ ',
        'ADS. ': 'ADS.\@ ',
        'RMT. ': 'RMT.\@ ',
        'NZ. ': 'NZ.\@ ',
        'M.T. ': 'M.T.\@ ',
        'Horowhenua': 'Horo\-whenua',
        'HQ. C.O.': 'HQ.\@ C.O.',
        'C.O. Battalion dinner': 'C.O.\@ Battalion dinner',
        'GA. So': 'GA.\@ So',
        'Trémouille': 'Tré\-mouille',
        'or M&V.': 'or M\\&V.',
    }

def latex_preamble():
    """Return the latex preamble to be added to the transformed document"""

    curdir = os.path.dirname(os.path.abspath(__file__))
    prefile = os.path.join(curdir, 'latex_preamble.tex')
    with open(prefile) as r:
        return r.read()


def latex_front_matter():
    """Return string to be inserted after the latex preamble but before the 
    transformed text.

    Normal usage is to fiddle about with package options."""

    return '\n'.join([
                '\\begin{document}',
                '\\tableofcontents',
                '\setcounter{secnumdepth}{-2}',
                '\include{./introduction}',
                '\lineation{page}',
                '\setlength{\stanzaindentbase}{30pt}',
                '\setstanzaindents{3,1,1}',
                '\setcounter{stanzaindentsrepetition}{1}',
                '\\newcommand*{\startstanzahook}{\\vspace{9pt}}',
                '\def\endstanzaextra{\\vspace{9pt}}',
                '\\allsectionsfont{\\normalsize}',
                '\\beginnumbering',
                ])

def latex_back_matter():
    """Return string to be inserted after the transformed text but before the document ends.
    Normal usage is to add backmatter like glossaries, works cited and indices."""

    return '\n'.join([
        '\endnumbering',
        '\clearpage',
        '\\rfoot{\\textsc{Glossary} / \\thepage}',
        '\printglossaries',
        '\clearpage',
        '\\rfoot{\\textsc{References} / \\thepage}',
        '\printbibliography',
        '\clearpage',
        '\\rfoot{\\textsc{Editorial Practice} / \\thepage}',
        '\\rfoot{\\textsc{Index / \\thepage}}',
        '\printindex',
        '\end{document}',
        ])

