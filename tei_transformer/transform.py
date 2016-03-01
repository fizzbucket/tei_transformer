"""Transform a tei file."""

# argparse is also imported
import os
import re
import subprocess
import sys
from collections import namedtuple
from functools import partial

from lxml import etree
from path import Path

from .tags import parser
from .config import config, update_config


class Transformer():

    """Transform resources, latexify the text produced, and make a pdf"""

    def __init__(self, force, inputpaths, textwraps, workfiles):
        bare_text = self.transform(*inputpaths)
        latex = self.latexify(bare_text, *textwraps)
        self.make_pdf(latex, force, *workfiles)

    def transform(self, inputpath, personlistpath):
        """Transform xml to tex"""
        body = parser.parse(inputpath).getroot().find('.//{*}body')
        assert body is not None
        tree = parser.transform_tree(body, PersDict(personlistpath))
        return '\n'.join(tree.itertext()).strip()

    @staticmethod
    def latexify(bare_text, before, after):
        """Wrap tex in preamble, intro, appendices, etc,
        and apply any replacements and substitutions"""
        text = '\n'.join([before, bare_text, after])
        for fix in config['string_replacements']:
            text = text.replace(*fix)
        for fix in config['regex_replacements']:
            text = re.sub(*fix, text)
        return text

    @staticmethod
    def make_pdf(latex, force, working_tex, working_pdf, out_pdf):
        """Make a pdf"""
        missing = not working_pdf.exists() or not working_tex.exists()
        if force or missing or hash(working_tex.text()) != hash(latex):
            working_tex.write_text(latex)
            call_cmd = config['caller_command']
            latexmk = '{c} {w}'.format(c=call_cmd, w=working_tex).split()
            subprocess.call(latexmk)
        assert working_pdf.exists()
        working_pdf.copy(out_pdf)

class Resources():

    """Filepaths and resource texts for transformation; 
        returns a namedtuple containing inputpaths for transformation,
        text for wrapping the transformed inputpaths in to make a tex file,
        and paths for writing temporary versions of tex and pdf, as well as the
        final output pdf"""

    def __new__(cls, inputpath, outname=None, standalone=False):
        r = cls._Resources(inputpath, outname, standalone)
        return r.freeze()

    def __init__(self):
        pass
    
    class _Resources():

        def __init__(self, inputpath, outname, standalone):
            self.standalone = standalone
            self.basepaths = self.BasePathMaker(inputpath, outname)
            self._processed_resources = self._process_resources()

        def _resources_by_classification_key(self, key):
            return iter(self.processed_resources[key])

        def parsepaths(self):
            parsepath_resources = self._resources_by_classification_key('parsepaths')
            return tuple(self.basepaths.inputpath, *parsepath_resources)

        def texts(self):
            before = self._resources_by_classification_key('before_text')
            after = self._resources_by_classification_key('after_text')
            return map('\n'.join, [before, after])

        def workpaths(self):
            return tuple(*self.basepaths.working_paths())

        def freeze(self):
            nt = namedtuple('Paths', ['inputpaths', 'textwraps', 'workfiles'])
            return nt(self.parsepaths(), self.texts(), self.workpaths())

        def _process_resources(self):

            def _rp_args(self):
                bp = self.basepaths
                return bp.work_dir, bp.resource_dir, bp.basename

            resourceprocessor = self.ResourceProcessor(self.standalone, *_rp_args())
            classifications = config['resource_classifications']
            return {k: [resourceprocessor(r) for r in v] for k, v
                    in classifications.items()} # Note possibility of hidden resources.

        class ResourceProcessor():

            def __init__(self, standalone, work_dir, resource_dir, basename):
                self.work_dir = work_dir
                self.resource_dir = resource_dir
                self.standalone = standalone
                self.resources = config['resources']

            def __call__(self, resource_name):
                resource = self.resources[resource_name]
                name, text = self._read_resource(resource)
                if resource.get('output') == 'read':
                    return text
                return self._write_resource(name, text)

            def _resource_values(self, resource):
                yield resource.get('name') or self.basename + resource['ext']
                yield from map(resource.get, ['required', 'subst'])

            def _read_resource(self, resource):
                name, required, subst = self._resource_values(resource)
                try:
                    text = self.resource_dir.joinpath(name).text()
                except FileNotFoundError as err:
                    no_sub = subst in [None, False]
                    if self.required or no_sub:
                        raise err
                    text = self._substitute_resource(resource, subst)
                return name, text

            def _substitute_resource(self, resource, subst):
                sub_include = resource.get('sub_include')
                if not sub_include or self.standalone:
                    return subst
                _sub = {'name': sub_include['name'],
                        'subst': sub_include.get('subst') or ''}
                r = self._read_resource(_sub)
                w = self._write_resource(*r)
                i = w.namebase if w else '%'
                include = '\\include{%s}' % i
                return subst % include

            def _write_resource(self, name, text):
                path = self.work_dir.joinpath(name)
                path.write_text(text)
                return path

        class BasePathMaker():

            def __init__(self, inputpath, outname):
                self.inputpath = Path(inputpath)
                self.curdir = self._curdir()
                self.basename = inputpath.namebase
                self.outname = outname or self.basename + '.pdf'
                # properties
                self._work_dir = None
                self._resource_dir = None

            def _curdir(self):
                curdir = Path(self.inputpath.dirname() or os.curdir)
                update_config(curdir)
                return curdir

            @property
            def work_dir(self):
                if not self._work_dir:
                    self._work_dir = self.curdirjoin(config['workdir'])
                    if not self._work_dir.exists():
                        self._work_dir.mkdir()
                return self._work_dir

            @property
            def resource_dir(self):
                if not self._resource_dir:
                    self._resource_dir = self.curdirjoin('resources')
                    if not self._resource_dir.exists():
                        raise IOError('Resources folder does not exist')
                return self._resource_dir

            def curdirjoin(self, addpath):
                return self.curdir.joinpath(addpath)

            def extendbasename(self, ext):
                return self.work_dir.joinpath(self.basename + ext)

            def working_paths(self):
                yield from map(self.extendbasename, ['.tex', '.pdf'])
                yield outname

class PersDict():

    def __new__(cls, path):
        d = cls.people(path)
        persdict = {x: p(d) for x, p in d.items()}
        return cls.name_t_persdict(persdict)

    def __init__(self):
        pass

    @classmethod
    def people(cls, path):
        personlist = parser.parse(path).getroot()
        people = personlist.iter('{*}person')
        return {p.xml_id: p for p in map(cls.Person, people)}


    @staticmethod
    def name_t_persdict(d):
        p_tuple = namedtuple('Person',
             ['xml_id', 'indexname',
              'indexonly', 'description'])
        return {xml_id: p_tuple(*person) for xml_id, person in d.items()}


    class Person():
        """A person."""

        def __init__(self, tag):
            self.xml_id = self._xml_id(tag)
            self.indexonly = self._indexonly(tag)
            i_and_d = self._indexname_and_description(tag)
            self.indexname, self.description = i_and_d

        def __call__(self, persdict):
            """Update description by parsing using persdict."""
            description, trait = self.description
            if trait is not None:
                parser.transform_tree(trait, persdict, in_body=False)
            trait = self._stripstring(trait)
            self.description = description(trait)
            return (self.xml_id, self.indexname,
                    self.indexonly, self.description)

        @staticmethod
        def _xml_id(tag):
            return tag.get('{%s}id' % config['xml_namespace'])

        @staticmethod
        def _indexonly(tag):
            iattr = tag.get('indexonly') in ['true', 'True']
            itag = tag.find('{*}indexonly') is not None
            return iattr or itag

        @classmethod
        def _find_string(cls, parent, query):
            tags = parent.iter('{*}' + query)
            matches = (cls._stripstring(m) for m in tags)
            return ' '.join(matches)

        @classmethod
        def _indexname_and_description(cls, tag):
            indexname, name = cls._get_names(tag)
            dates = cls._get_dates(tag)
            return indexname, cls._get_partial_description(tag, name, dates)

        @classmethod
        def _get_names(cls, tag):
            namefinder = partial(cls._find_string, tag.find('{*}persName'))
            nametags = ['forename', 'addName', 'surname']
            firstnames, addnames, surnames = map(namefinder, nametags)
            addnames = "`%s'" % addnames if addnames else ''
            all_names = [' '.join([firstnames, addnames]), surnames]
            indexname = ', '.join(reversed(all_names)).strip()
            name = ' '.join(all_names).strip()
            return indexname, name

        @classmethod
        def _get_dates(cls, tag):
            date_finder = partial(cls._find_string, tag)
            date_targets = ['birth', 'death']
            return map(date_finder, date_targets)

        @staticmethod
        def _get_partial_description(tag, name, dates):
            descript_fmt = '{} ({}--{}) {}'.format
            descript_part = partial(descript_fmt, name, *dates)
            trait_tag = tag.find('{*}trait')
            return descript_part, trait_tag


        @staticmethod
        def _stripstring(tag):
            try:
                return str(tag.text).strip()
            except AttributeError:
                return ''


def main():
    """Parse arguments and transform."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("inputname",
                        help="TEI file to transform")
    parser.add_argument("-o", "--outputname",
                        help="Filename of the transformed file.",
                        default=None)
    parser.add_argument("-f", "--force",
                        help="Force recompilation even if unchanged.",
                        action="store_true")
    parser.add_argument('-s', '--standalone',
                        help="Do not include introduction or appendices",
                        action="store_true")
    args = parser.parse_args(sys.argv[1:])
    resources = Resources(args.inputname, args.outputname, args.standalone)
    Transformer(args.force, *resources)


if __name__ == '__main__':
    main()
