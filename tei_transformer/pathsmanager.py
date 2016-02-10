import textwrap
import os
from functools import partial

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

# Substitutions when not present

AFTER_PREAMBLE_SUBST = '\\begin{document}'
AFTER_TEXT_END_SUBST = textwrap.dedent("""\
        \\endnumbering
        \\backmatter
        %s
        \\printbibliography
        \\printindex
        \\end{document}
        """)
AFTER_TEXT_START_SUBST = textwrap.dedent("""\
        \\frontmatter
        \\tableofcontents
        %s
        \\mainmatter
        \\beginnumbering
        """)

DEFAULT_INDEX_STYLE = textwrap.dedent("""\
        headings_flag 1
        heading_prefix "{\\\\bfseries "
        heading_suffix "}\\\\nopagebreak\\n"
        """)


class PathManager():

    def __init__(self, inputpath, outputname=None, standalone=False):
        self.basename = Path(outputname or inputpath).namebase
        self.inputpath = Path(inputpath)
        curdir = Path(inputpath.dirname() or os.curdir)
        self.extend_curdir(curdir)
        self.standalone = standalone

    # Only the following three functions will be called.

    def inputpaths(self):
        """Paths needed for parsing"""
        inputpath = self.inputpath
        personlistpath = self._resource_path(PERSONLIST_NAME, required=True)
        return inputpath, personlistpath

    def textwraps(self):
        """Strings for wrapping parsed text to make a .tex file"""
        before_text = self.before_text()
        after_text = self.after_text()
        return before_text, after_text

    def workfiles(self):
        """Paths for calling latexmk with"""
        out_pdf = self.basename + '.pdf'
        working_tex = self._ewb('.tex')
        working_pdf = self._ewb('.pdf')
        return working_tex, working_pdf, out_pdf

    def hidden_requirements(self):
        """We don't use these but latex might"""
        self._references()
        self._indexstyle()

    # Administrative bits

    def extend_curdir(self, curdir):
        ec = partial(self.extend_dir, curdir)
        self.workdir(ec)
        self.resourcedir(ec)

    def workdir(self, extend_curdir):
        workdir = extend_curdir(WORKDIR_NAME)
        if not workdir.exists():
            workdir.mkdir()
        self._extend_workdir = partial(self.extend_dir, workdir)
        self._ewb = lambda x: self._extend_workdir(self.basename + x)

    def resourcedir(self, extend_curdir):
        resourcedir = extend_curdir(RESOURCEDIR_NAME)
        if not resourcedir.exists():
            raise IOError('You need to provide a folder of resources.')
        self._extend_resourcedir = partial(self.extend_dir, resourcedir)

    def extend_dir(self, original, extension):
        extended = original.joinpath(extension)
        return Path(extended)

    def _resource_path(self, name, required=False):
        """Make a resource path"""
        r = self._extend_resourcedir(name)
        w = self._extend_workdir(name)
        if not r.exists() and required:
            raise FileNotFoundError(r)
        if not w.exists():
            if r.exists():
                    r.copy2(w)
        else:
            if not r.read_md5() == w.read_md5():
                r.copy2(w)
        return w

    # Hidden requirements

    def _references(self):
        return self._resource_path(REFERENCES_NAME, required=True)

    def _indexstyle(self):
        p = self._ewb('.mst')
        if not p.exists():
            r = DEFAULT_INDEX_STYLE
            p.write_text(r)

    # Making the textwrap bits

    def before_text(self):
        return '\n'.join(self._parts_before_text())

    def after_text(self):
        return '\n'.join(self._parts_after_text())

    def _parts_before_text(self):
        parts = [self._preamble,
                 self._after_preamble,
                 self._after_text_start]
        for part in parts:
            yield part()

    def _parts_after_text(self):
        parts = [self.after_text_end]
        for part in parts:
            yield part()

    def _preamble(self):
        preamble = self._resource_path(PREAMBLE_NAME, required=True)
        return preamble.text()

    def _handle_optional(self, name, subst=''):
        target = self._resource_path(name)
        try:
            return target.text()
        except IOError:
            return subst

    def _after_preamble(self):
        n = AFTER_PREAMBLE_NAME
        r = AFTER_PREAMBLE_SUBST
        return self._handle_optional(n, r)

    def _after_text_end(self):
        n = AFTER_TEXT_END_NAME
        r = AFTER_TEXT_END_SUBST % self._include(APPENDICES_NAME)
        return self._handle_optional(n, r)

    def _after_text_start(self):
        n = AFTER_TEXT_START_NAME
        r = AFTER_TEXT_START_SUBST % self._include(INTRODUCTION_NAME)
        return self._handle_optional(n, r)

    def _include(self, name):
        r = self._resource_path(name)
        if self.standalone or not r.exists():
            return '%'
        return '\\include{%s}' % r.namebase
