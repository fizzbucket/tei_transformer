import os
import subprocess
import re
import collections
import sys

from . import persdict
from . import parser
from .pathsmanager import PathManager


def transform_tei(inputname, outname=None,
                  force=False, quiet=False, standalone=False):
    """"Read inputname and transform to a pdf"""
    paths = PathManager(inputname, outputname=outname, standalone=standalone)

    inputpaths = paths.inputpaths()
    textwraps = paths.textwraps()
    workfiles = paths.workfiles()

    bare_text = Transform(*inputpaths)
    latex = LatexifiedText(bare_text, *textwraps)
    PDFMaker(str(latex), *workfiles, force, quiet)


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
        body = root.find('.//{*}body')  # {*} is to map any namespace
        assert body is not None
        tree = self.parser.transform_tree(body, self.persdict)
        return '\n'.join(tree.itertext()).strip()

    def __str__(self):
        return self.text


class LatexifiedText(collections.UserString):

    def __init__(self, text, before_text, after_text):
        super().__init__(text)
        self.before_latexify()
        self.latexify(before_text, after_text)
        self.after_latexify()

    def before_latexify(self):
        """Actions to take before text is latexified"""
        pass

    def latexify(self):
        components = [self.before_text,
                      self.data,
                      self.after_text]
        self.data = '\n'.join(components)

    def after_latexify(self):
        """Actions to take after text is latexified."""
        self._hyphenation_fixes()
        self._custom_replacements()
        self._whitespace_substitution()

    def _whitespace_substitution(self):
        """Normalise whitespace"""
        wspaces = [(r'\ +', ' '),  # Be a tidy kiwi.
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
        """Custom applications of replacements to text.
        Probably changes per project."""
        self.data = self.data.replace('HQ. C.O.', 'HQ.~C.O.')
        self.data = self.data.replace('C.O. Battalion', 'C.O.~Battalion')
        self.data = re.sub(r'([A-Z.]{2,})\.\ (?=[A-Z])', r'\1\@. ', self.data)


class PDFMaker():

    def __init__(self, latex, working_pdf, working_tex, out_pdf, force, quiet):
        self.working_tex = working_tex
        self.working_pdf = working_pdf
        self.quiet = quiet

        if self.check_run(latex, force):
            self.make_pdf()
        self.on_pdf_creation()

    class ConversionError(Exception):
        pass

    def on_pdf_creation(self):
        self.copy()

    def make_pdf(self):
        self.call_latex()
        if not self.working_pdf.exists():
            raise self.ConversionError('No PDF file was produced.')

    def call_latex(self):
        options = ['-bibtex',  # run biber for references
                   '-cd',  # change to working_directory to run
                   '-g',  # run even if unchanged.
                   '-pdf']
        latexmk_command = ['latexmk'] + options + [str(self.working_tex)]
        try:
            self._call(latexmk_command, self.quiet)
        except FileNotFoundError:  # no latexmk
            print('You need to install latexmk and pdflatex.')
            sys.exit()

    @staticmethod
    def _call(command, quiet):
        if quiet:
            with open(os.devnull, "w") as fnull:
                quiet_stdout = {'stdout': fnull, 'stderr': fnull}
                return subprocess.call(command, **quiet_stdout)
        return subprocess.call(command)

    def copy(self):
        """Copy working pdf to final destination"""
        self.working_pdf.copy(self.out_pdf)

    def check_run(self, latex, force):
        """Whether it is necessary to write tex and call latexmk"""

        if self._force_check() or self._compare_check():
            return self._write(latex)

        print('Unchanged since last run')
        return False

    def _force_check(self, force):
        no_pdf = not self.working_pdf.exists()
        no_tex = not self.working_tex.exists()

        if force or no_pdf or no_tex:
            return True

    def _compare_check(self, latex):
        return hash(self.working_tex.text()) != hash(latex)

    def _write(self, latex):
        self.working_tex.write(latex)
        return True
