import textwrap
import os

from path import Path

class PathManager():

    def __init__(self, inputname, outputname=None):
        basepaths = self.BasePaths(inputname)
        self.paths = self.FilePathsManager(basepaths)
        self.text = self.FilesReader(basepaths)
        self.latex = self.LatexTransformRequires(basepaths, outputname)

    class BasePaths():

        def __init__(self, inputname):
            self._inputpath = Path(inputname)
            self._basename = self._inputpath.namebase
            self._curdir = Path(self._inputpath.dirname() or os.curdir)
            self._workdir = self.extend_curdir('working_directory')
            if not self._workdir.exists():
                self._workdir.mkdir()
            self._resourcedir = self.extend_curdir('resources')
            if not self._resourcedir.exists():
                raise IOError('You need to provide a folder of resources.')
            self._personlist = None

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
            if not r.exists():
                if required:
                    raise FileNotFoundError(r)
                else:
                    print('Resource not found: %s' % name)
                    print('Will try to use substitute...')

            w = self.extend_workdir(name)

            if not w.exists() or not r.read_md5() == w.read_md5():
                if r.exists():
                    r.copy2(w)
            return w

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
                self._personlist = self.bp._resource_path('personlist.xml')
            return self._personlist

    class FilesReader():

        def __init__(self, basepaths):
            self.bp = basepaths
            self._make_hidden()

        def rp(self, name, r=False):
            return self.bp._resource_path(name, required=r)

        # Hidden requirements

        def _make_hidden(self):
            self.references()
            self.indexstyle()

        def references(self):
            return self.rp('references.bib', r=True)

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
            n = 'after_preamble.tex'
            r = '\\begin{document}'
            return self._handle_optional(n, r)

        def after_text_end(self):
            n = 'after_text_end.tex'
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
            n = 'after_text_start.tex'
            r = textwrap.dedent("""\
            \\frontmatter
            \\tableofcontents
            %s
            \\mainmatter
            \\beginnumbering
            """ % self.intro_include())
            return self._handle_optional(n, r)

        def introduction(self):
            n = 'introduction.tex'
            r = self.rp(n)
            if r.exists():
                return r

        def appendices(self):
            n = 'appendices.tex'
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
            if force:
                self.working_tex.write_text(latex)
                return True

            no_pdf = not self.working_pdf.exists()
            no_tex = not self.working_tex.exists()

            if no_pdf or no_tex:
                self.working_tex.write_text(latex)
                return True

            compare = hash(self.working_tex.text()) == hash(latex)
            if not compare:
                self.working_tex.write_text(latex)
                return True

            print('Unchanged since last run')
            return False

        def copy(self):
            """Copy working pdf to final destination"""
            self.working_pdf.copy(self.out_pdf)