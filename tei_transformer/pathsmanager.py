import textwrap
import os
from functools import partial
from itertools import chain

from path import Path

from .config import config, update_config

class PathManager():

    def __init__(self, inputpath, outputname=None, standalone=False):
        self.inputpath = Path(inputpath)
        self.basename = self.inputpath.namebase
        self.outputname = outputname or self.basename + '.pdf'
        self.standalone = standalone
        self._dirs()
        self.latex_only_requirements()

    def _process(self, rnamelist):
        return map(self.process_resource, [config['resources'][x] for x in rnamelist])

    def latex_only_requirements(self):
        return self._process(['references', 'indexstyle'])

    def parsing_paths(self):
        return self.inputpath, next(self._process(['personlist']))

    def textwraps(self):
        before_text = ['preamble', 'after_preamble', 'after_text_start']
        after_text = processor(['after_text_end'])
        return map('\n'.join, map(self._process, [before_text, after_text]))

    def latexmk_paths(self):
        working_tex, working_pdf = map(self.extend_workdir_b, ['.tex', '.pdf'])
        return working_tex, working_pdf, self.outputname

    def _dirs(self):
        curdir = self.inputpath.dirname() or os.curdir
        config.update_config(curdir)
        resourcedir = self._extend_dir(curdir, 'resources', required=True)
        workdir = self._extend_dir(curdir, config['workdir']['name'], make=True) 
        self.extend_resourcedir = partial(self._extend_dir, resource_dir)
        self.extend_workdir = partial(self._extend_dir, work_dir)
        self.extend_workdir_b = lambda ext: self.extend_workdir(self.basename + ext)

    @staticmethod
    def _extend_dir(original, extension, make=False, required=False):
        path = Path(original.joinpath(extension))
        if not path.exists():
            if make:
                path.mkdir()
            elif required:
                raise IOError(path)
        return path

    def process_resource(self, resource):
        name, required, subst = map(resource.get, ['name', 'required', 'subst'])
        name = name or self.basename + resource['ext']
        r = self.extend_resourcedir(name)
        w = self.extend_workdir(name)
        if not r.exists() and required:
            raise FileNotFoundError(r)
        try:
            text = resource.read_text()
        except FileNotFoundError as e:
            if subst in [None, False]:
                raise e
            text = self.process_subst(resource)
        if output == 'read':
            return text
        w.write_text(text)
        return w

    def process_subst(self, resource):
        sub_include = resource.get('sub_include')
        if sub_include and not self.standalone:
            _sub = {'name': sub_include['name'], 'subst': sub_include.get('subst') or ''}
            sub_include = self.make_resource_path(_sub)
            i = sub_include.namebase if sub_include else '%'
            include = '\\include{%s}' % i
            return subst % include
        return subst

def pathmanager(*args, **kwargs):
    manager = PathManager(*args, **kwargs)
    return manager.parsing_paths(), manager.textwraps(), manager.latexmk_paths()
