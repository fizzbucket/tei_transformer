import filecmp
import os
import textwrap
import shutil

class Path():

    def __init__(self, p):
        self._path = str(p)

    def __str__(self):
        return self._path

    def stem(self):
        name = self.basename()
        i = name.rfind('.')
        if 0 < i < len(name) - 1:
            return name[:i]
        else:
            return name

    def basename(self):
        return os.path.basename(self._path)

    def dirname(self):
        return os.path.dirname(self._path)

    def read(self, flag='r'):
        with open(self._path, flag) as i:
            return i.read()

    def write(self, text, flag='w'):
        with open(self._path, flag) as o:
            o.write(text)

    def exists(self):
        return os.path.exists(self._path)

    def is_file(self):
        return os.path.isfile(self._path)

    def is_dir(self):
        return os.path.isdir(self._path)

    def hash_compare(self, text):
        one = hash(self.read())
        two = hash(text)
        return one == two
        
    def file_compare(self, path):
        return filecmp.cmp(self._path, str(path))

    def copy_to(self, path):
        print('Copying %s to %s' % (self._path, str(path)))
        return shutil.copy2(self._path, str(path))


class FilePath(Path):

    def __init__(self, path):
        super().__init__(path)

    def add(self, addendum):
        raise NotADirectoryError(self._path)

    def check(self):
        return self.exists() and self.is_file()

    def unlink(self):
        return os.unlink(self._path)

    def rmdir(self):
        raise NotADirectoryError(self_path)


class DirPath(Path):

    def __init__(self, path):
        super().__init__(path)
        try:
            self.mkdir()
        except FileExistsError:
            pass

    def extend(self, addendum):
        return os.path.join(self._path, str(addendum))

    def check(self):
        return self.exists() and self.is_dir()

    def mkdir(self):
        if not self.check():
            os.mkdir(self._path)
        else:
            raise FileExistsError(self._path)

    def unlink(self):
        raise IsADirectoryError(self._path)


class RequiredPath(FilePath):

    def __init__(self, path):
        super().__init__(path)
        self.check()

    def check(self):
        if not super().check():
            raise IOError(self._path)

class DefaultPath(FilePath):
    """ A subclass of FilePath with a change; if the file does not exist,
    attempts to read or copy it are intercepted and whatever returned by 
    _substitute(self) are used instead. This allows the replacement of a
    missing file in a way invisible to the caller."""

    def __init__(self, path):
        super().__init__(path)
        self._sub_text = ''

    def read(self, flag='r'):
        if self.check():
            return super().read(flag=flag)
        sub = self._substitute()
        return sub

    def copy_to(self, destination):
        if self.check():
            return super().copy_to(str(destination))
        sub = self._substitute()
        if isinstance(destination, Path):
            destination.write(sub)
        else:
            with open(destination, 'w') as o:
                o.write(sub)

    def _substitute(self):
        return self._sub_text

    def hash_compare(self, other):
        if not self.check():
            return False
        return super().hash_compare(other)

    def file_compare(self, other):
        if not self.check():
            return False
        return super().file_compare(other)


class ResourcePath(FilePath):

    """Path representing a resource."""

    def __init__(self, resource_path, work_path, required=True):
        super().__init__(work_path)
        self.required = required
        if self.required:
            self.resource_path = RequiredPath(resource_path)
        else:
            self.resource_path = DefaultPath(resource_path)

    def _copy_resource(self):
        if not self.check() or not self.resource_path.file_compare(self):
            self.resource_path.copy_to(self)

class ResourcePathMaker():

    def __init__(self, paths):
        self.paths = paths
        self._sub_dict = {'indexstyle': self._indexstyle_sub,
                'beforetext': self._beforetext_sub,
                'aftertextend': self._after_text_sub,
                'afterpreamble': self._after_preamble_sub}

    @property
    def intro_stem(self):
        return self.paths.introduction.stem() or ''

    @property
    def append_stem(self):
        return self.paths.appendices.stem() or ''
    
    def __call__(self, name, required=True, key=None):
        work_path = self.paths.workdir.extend(name)
        resource_path = self.paths.resourcedir.extend(name)
        made = ResourcePath(resource_path, work_path, required=required)
        if not required and key:
            made.resource_path._sub_text = self._sub_dict[key]()
        made._copy_resource()
        return made

    def _set_sub_text(self, key):
        self._sub_text = self._sub_dict[key]()
        
    def _indexstyle_sub(self):
        return textwrap.dedent("""\
            headings_flag 1
            heading_prefix "{\\\\bfseries "
            heading_suffix "}\\\\nopagebreak\\n"
            """)

    def _beforetext_sub(self):
        return textwrap.dedent("""\
            \\frontmatter
            \\tableofcontents%s
            \\mainmatter
            \\beginnumbering
            """ % self.include_stem(self.intro_stem))

    def _after_text_sub(self):
        return textwrap.dedent("""\
            \\endnumbering
            \\backmatter%s
            \\printbibliography
            \\printindex
            \\end{document}
            """ % self.include_stem(self.append_stem))

    def _after_preamble_sub(self):
        return '\\begin{document}'

    @staticmethod
    def include_stem(stem):
        if stem:
            return '\n\\include{%s}' % stem
        return stem


class PathManager():

    def __init__(self, inputname, outputname=None):

        self._make_curdirpaths(inputname, outputname)
        self._make_resourcepaths()
        self._make_workdirpaths()

    def _make_curdirpaths(self, inputname, outputname):
        
        self.inputpath = FilePath(inputname)
        self._basename = self.inputpath.stem()

        curdir = DirPath(self.inputpath.dirname() or os.curdir)
        wd = curdir.extend('working_directory')
        self.workdir = DirPath(wd)
        rd = curdir.extend('resources')
        self.resourcedir = DirPath(rd)

        outpdfname = outputname or self._basename + '.pdf'
        op = curdir.extend(outpdfname)
        self.out_pdf = FilePath(op)

    def _make_workdirpaths(self):
        wt = self.workdir.extend(self._basename + '.tex')
        self.working_tex = FilePath(wt)
        wp = self.workdir.extend(self._basename + '.pdf')
        self.working_pdf = FilePath(wp)

    def _make_resourcepaths(self):
        rmkr = ResourcePathMaker(self)
        self.preamble = rmkr('latex_preamble.tex')
        self.references = rmkr('references.bib')
        self.personlist = rmkr('personlist.xml')
        # Optional ones
        self.introduction = rmkr('no_introduction.tex',
                                    required=False)
        self.appendices = rmkr('no_appendices.tex',
                                    required=False)
        self.indexstyle = rmkr(self._basename + '.mst',
                                    required=False,
                                    key='indexstyle')
        self.after_preamble = rmkr('after_preamble.tex',
                                    required=False,
                                    key='afterpreamble')
        self.after_text_start = rmkr('after_text_start.tex',
                                    required=False,
                                    key='beforetext')
        self.after_text_end = rmkr('after_text_end.tex',
                                    required=False,
                                    key='aftertextend')

    @staticmethod
    def is_required_resource(path):
        return True

    @staticmethod
    def is_optional_resource(path):
        return True
        