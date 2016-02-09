import textwrap
import os

from path import Path

# Directory constants
WORKDIR_NAME = 'working_directory'
RESOURCEDIR_NAME = 'resources'

# XML constants: required.
PERSONLIST_NAME = 'personlist.xml'
REFERENCES_NAME = 'references.bib'

# Latex Constants
# ... required
PREAMBLE_NAME = 'latex_preamble.tex'
# ... not required
AFTER_PREAMBLE_NAME = 'after_preamble.tex'
INTRODUCTION_NAME = 'introduction.tex'
APPENDICES_NAME = 'appendices.tex'
AFTER_TEXT_END_NAME = 'after_text_end.tex'
AFTER_TEXT_START_NAME = 'after_text_start.tex'


class PathManager():

    def __init__(self, inputname, outputname=None, standalone=False):
        basepaths = BasePaths(inputname)
        self.paths = FilePathsManager(basepaths)
        self.text = FilesReader(basepaths, standalone)
        self.latex = LatexTransformRequires(basepaths, outputname)


class BasePaths():

    def __init__(self, inputname):
        self._from_inputname()
        self._workdir = self._i_workdir()
        self._resourcedir = self._i_resourcedir()
        self._personlist = None

    def _from_inputname(self, inputname):
        self._inputpath = Path(inputname)
        self._basename = self._inputpath.namebase
        self._curdir = Path(self._inputpath.dirname() or os.curdir)

    def _i_workdir(self):
        self._workdir = self.extend_curdir(WORKDIR_NAME)
        if not self._workdir.exists():
            self._workdir.mkdir()

    def _i_resourcedir(self):
        self._resourcedir = self.extend_curdir(RESOURCEDIR_NAME)
        if not self._resourcedir.exists():
            raise IOError('You need to provide a folder of resources.')

    def _extend_path(self, original, extension):
        extended = original.joinpath(extension)
        return Path(extended)

    def extend_curdir(self, extension):
        return self._extend_path(self._curdir, extension)

    def extend_workdir(self, extension):
        return self._extend_path(self._workdir, extension)

    def extend_resourcedir(self, extension):
        return self._extend_path(self._resourcedir, extension)

    def _resource_path(self, name, required=False):
        r = self.extend_resourcedir(name)
        w = self.extend_workdir(name)

        if not r.exists() and required:
            raise FileNotFoundError(r)

        if not w.exists():
            self._resource_path_no_working(r, w)
        else:
            self._resource_path_working_exists(r, w)

        return w

    def _resource_path_no_working(self, resourcepath, workpath):
        if resourcepath.exists():
                resourcepath.copy2(workpath)

    def _resource_path_working_exists(self, r, w):
        if not r.read_md5() == w.read_md5():
            r.copy2(w)


class FilePathsManager():

    def __init__(self, basepaths):
        self.bp = basepaths
        self._personlist = None

    @property
    def inputpath(self):
        return self.bp._inputpath

    @property
    def personlist(self):
        if not self._personlist:
            self._personlist = self.bp._resource_path(PERSONLIST_NAME)
        return self._personlist


class FilesReader():

    def __init__(self, basepaths, standalone):
        self.bp = basepaths
        self._make_hidden()
        self.standalone = standalone

    def rp(self, name, r=False):
        return self.bp._resource_path(name, required=r)

    # Hidden requirements

    def _make_hidden(self):
        self.references()
        self.indexstyle()

    def references(self):
        return self.rp(REFERENCES_NAME, r=True)

    def indexstyle(self):
        p = self.bp.extend_workdir(self.bp._basename + '.mst')
        if not p.exists():
            r = textwrap.dedent("""\
            headings_flag 1
            heading_prefix "{\\\\bfseries "
            heading_suffix "}\\\\nopagebreak\\n"
            """)
            p.write_text(r)

    # Mandatory

    def preamble(self):
        preamble = self.rp('latex_preamble.tex', r=True)
        return preamble.text()

    # Optional

    def _handle_optional(self, name, subst=''):
        target = self.rp(name)
        if target.exists():
            return target.text()
        return subst

    def after_preamble(self):
        n = AFTER_PREAMBLE_NAME
        r = '\\begin{document}'
        return self._handle_optional(n, r)

    def after_text_end(self):
        n = AFTER_TEXT_END_NAME
        r = textwrap.dedent("""\
        \\endnumbering
        \\backmatter
        %s
        \\printbibliography
        \\printindex
        \\end{document}
        """ % self.appendices_include())
        return self._handle_optional(n, r)

    def intro_include(self):
        if self.introduction():
            return '\\include{%s}' % self.introduction().namebase
        return '%'

    def appendices_include(self):
        if self.appendices():
            return '\\include{%s}' % self.appendices().namebase
        return '%'

    def after_text_start(self):
        n = AFTER_TEXT_START_NAME
        r = textwrap.dedent("""\
        \\frontmatter
        \\tableofcontents
        %s
        \\mainmatter
        \\beginnumbering
        """ % self.intro_include())
        return self._handle_optional(n, r)

    def introduction(self):
        if self.standalone:
            return None
        n = INTRODUCTION_NAME
        r = self.rp(n)
        if r.exists():
            return r

    def appendices(self):
        if self.standalone:
            return None
        n = APPENDICES_NAME
        r = self.rp(n)
        if r.exists():
            return r


class LatexTransformRequires():

    def __init__(self, basepaths, outputname):
        self.ew = basepaths.extend_workdir
        self._basename = basepaths._basename
        self._outputname = outputname

        self._working_tex = None
        self._working_pdf = None
        self._out_pdf = None

    @property
    def working_tex(self):
        if not self._working_tex:
            self._working_tex = self.ew(self._basename + '.tex')
        return self._working_tex

    @property
    def working_pdf(self):
        if not self._working_pdf:
            self._working_pdf = self.ew(self._basename + '.pdf')
        return self._working_pdf

    @property
    def out_pdf(self):
        if not self._out_pdf:
            outname = self._outputname or self._basename + '.pdf'
            self._out_pdf = outname
        return self._out_pdf

    def check_run(self, latex, force):
        """Whether it is necessary to write tex and call latexmk"""

        no_pdf = not self.working_pdf.exists()
        no_tex = not self.working_tex.exists()

        if force or no_pdf or no_tex:
            return self._write(latex)

        compare = hash(self.working_tex.text()) == hash(latex)
        if not compare:
            return self._write(latex)

        print('Unchanged since last run')
        return False

    def _write(self, latex):
        self.working_tex.write(latex)
        return True

    def copy(self):
        """Copy working pdf to final destination"""
        self.working_pdf.copy(self.out_pdf)
