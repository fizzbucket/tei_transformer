import os
import subprocess
import re
import textwrap
import collections
import sys

from . import persdict
from . import parser
from .pathsmanager import PathManager

def transform_tei(inputname, outname=None, force=False, quiet=False):

    paths = PathManager(inputname, outputname=outname)
    bare_text = Transform(paths.paths.inputpath, paths.paths.personlist)
    latex = LatexifiedText(bare_text, paths.text)
    pdf = PDFMaker(str(latex), paths.latex, force, quiet)

class Transform():

    def __init__(self, inputpath, personlistpath, use_persdict=True):

        self.personlist = personlistpath
        self.filepath = inputpath
        self.use_persdict = use_persdict

        self.parser = parser.Parser()
        self.persdict = self._persdict()

        self.text = self.transform()

    def _persdict(self):
        if self.use_persdict:
            return persdict.PersDict(self.personlist, self.parser)

    def transform(self):
        tree = self.parser(self.filepath)
        root = tree.getroot()
        body = root.find('.//{*}body') # {*} is to map any namespace
        assert body is not None
        tree = self.parser.transform_tree(body, self.persdict)
        return '\n'.join(tree.itertext()).strip()

    def __str__(self):
        return self.text



class LatexifiedText(collections.UserString):

    def __init__(self, text, tex_components):
        super().__init__(text)
        self.tex_components = tex_components
        self.before_latexify()
        self.latexify()
        self.after_latexify()

    def before_latexify(self):
        """Actions to take before text is latexified"""
        pass

    def latexify(self):
        self.data = '\n'.join(self._document_parts())

    def _document_parts(self):
        for part in [self.tex_components.preamble,
                    self.tex_components.after_preamble,
                    self.tex_components.after_text_start,
                    self.text,
                    self.tex_components.after_text_end]:
            yield part()

    def text(self):
        return self.data

    def after_latexify(self):
        """Actions to take after text is latexified."""
        self._hyphenation_fixes()
        self._custom_replacements()
        self._whitespace_substitution()

    def _whitespace_substitution(self):
        """Normalise whitespace"""
        wspaces = [(r'\ +', ' '), # Be a tidy kiwi.
                (r'\n\ +', '\n'),
                (r'\n\n+', '\n\n'),
               ]
        for match in wspaces:
            m, r = match
            self.data = re.sub(m, r, self.data)


    def _hyphenation_fixes(self):
        """Add hyphenation points to words. Probably changes per project."""
        self.data = self.data.replace('Horowhenua', 'Horo\-whenua')
        self.data = self.data.replace('Trémouille', 'Tré\-mouille')

    def _custom_replacements(self):
        """Custom applications of replacements to text. Probably changes per project."""
        self.data = self.data.replace('HQ. C.O.', 'HQ.~C.O.')
        self.data = self.data.replace('C.O. Battalion', 'C.O.~Battalion')
        self.data = re.sub(r'([A-Z.]{2,})\.\ (?=[A-Z])', r'\1\@. ', self.data)

class PDFMaker():

    def __init__(self, latex, paths, force, quiet):
        self.paths = paths
        self.quiet = quiet

        if self.paths.check_run(latex, force):
            self.make_pdf()
        self.on_pdf_creation()

    class ConversionError(Exception):
        pass

    def on_pdf_creation(self):
        self.paths.copy()

    def make_pdf(self):
        self.call_latex()
        if not self.paths.working_pdf.exists():
            raise self.ConversionError('No PDF file was produced.')

    def call_latex(self):
        options = ['-bibtex', # run biber for references
           '-cd', # change to working_directory to run
           #'-f', # force through errors
           '-g', # run even if unchanged.
           '-pdf',]
        latexmk_command = ['latexmk'] + options + [str(self.paths.working_tex)]
        try:
            if self.quiet:
                with open(os.devnull, "w") as fnull:
                    return subprocess.call(latexmk_command, stdout = fnull, stderr = fnull)
            return subprocess.call(latexmk_command)
        except FileNotFoundError: # no latexmk
            print('You need to install latexmk and pdflatex.')
            sys.exit()
