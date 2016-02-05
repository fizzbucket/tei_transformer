import os
import subprocess
import re
import textwrap
import collections

from . import persdict
from . import parser
from .pathsmanager import PathManager

def transform_tei(inputname, outname=None, force=False, quiet=False):

    paths = PathManager(inputname, outputname=outname)
    bare_text = Transform(paths)
    latex = LatexifiedText(bare_text, paths)
    pdf = PDFMaker(latex, paths, force, quiet)

class ConversionError(Exception):
    pass

class Transform():

    def __init__(self, paths, use_persdict=True):

        self.filepath = paths.inputpath
        self.working_directory = paths.workdir
        self.paths = paths
        self.use_persdict = use_persdict

        self.parser = parser.Parser()
        self.persdict = self._persdict()

        self.text = self.transform()

    def _persdict(self):
        if self.use_persdict:
            return persdict.PersDict(self.paths, self.parser)

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

    def __init__(self, text, paths):
        super().__init__(text)
        self.paths = paths
        self.before_latexify()
        self.latexify()
        self.after_latexify()

    def before_latexify(self):
        """Actions to take before text is latexified"""
        pass

    def latexify(self):
        self.data = '\n'.join(self._document_parts())

    def _document_parts(self):
        for part in [self._preamble,
                    self._after_preamble,
                    self._after_text_start,
                    self._get_base_text,
                    self._after_text_end]:
            yield part()

    def _get_base_text(self):
        return self.data

    def _preamble(self):
        """Return string to form the preamble of the latex document"""
        return self.paths.preamble.read()
    
    def _after_preamble(self):
        return self.paths.after_preamble.read()

    def _after_text_start(self):
        """Return string to include after '\\begin{document}' but before text"""
        intro_stem = self.paths.introduction.stem
        return self.paths.after_text_start.read()

    def _after_text_end(self):
        """Return string to include after text. Should end with '\\end{document}"""
        appendices_stem = self.paths.appendices.stem
        return self.paths.after_text_end.read()

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
          self.data = re.sub(*match, self.data)


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
        self.latex = latex
        self.force = force
        self.paths = paths
        self.quiet = quiet

        self.worktex = self.paths.working_tex
        self.workpdf = self.paths.working_pdf

        if self.check_run():
            self.make_pdf()
        self.on_pdf_creation()

    def check_run(self):
        no_pdf = not self.workpdf.exists()
        no_tex = not self.worktex.exists()

        if self.force or no_pdf or no_tex:
            return True
        elif not self.worktex.hash_compare(self.latex):
            return True
        else:
            print('Has not changed since the last run')

    def on_pdf_creation(self):
        self.workpdf.copy_to(self.paths.out_pdf)

    def make_pdf(self):
        self.worktex.write(str(self.latex))
        self.call_latex()
        if not self.workpdf.exists():
            raise ConversionError('No PDF file was produced.')

    def call_latex(self):
        options = ['-bibtex', # run biber for references
           '-cd', # change to working_directory to run
           '-f', # force through errors
           '-g', # run even if unchanged.
           '-pdf',]
        latexmk_command = ['latexmk'] + options + [str(self.worktex)]
        if self.quiet:
            with open(os.devnull, "w") as fnull:
                return subprocess.call(latexmk_command, stdout = fnull, stderr = fnull)
        return subprocess.call(latexmk_command)
