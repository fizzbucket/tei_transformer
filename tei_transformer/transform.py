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
        body = parser.parse(inputpath).getroot().find('.//{*}body')
        assert body is not None
        tree = parser.transform_tree(body, PersDict(personlistpath))
        return '\n'.join(tree.itertext()).strip()

    @staticmethod
    def latexify(bare_text, before, after):
        text = '\n'.join([before, bare_text, after])
        for fix in config['string_replacements']:
            text = text.replace(*fix)
        for fix in config['regex_replacements']:
            text = re.sub(*fix, text)
        return text

    @staticmethod
    def make_pdf(latex, force, working_tex, working_pdf, out_pdf):
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

    def __new__(cls, *args, **kwargs):
        inputpath, outputname, resource_maker, basename_maker = \
            cls._get_args(*args, **kwargs)

        classifications = config['resource_classifications']
        resources = {k: [resource_maker(r) for r in v] for k, v
                     in classifications.items()}

        def groups(target):
            return iter(resources[target])

        # input path, path to personlist
        parsepaths = inputpath, next(groups('parsepath'))
        # text to go before and after transformed inputpath
        texts = map('\n'.join, map(groups, ['before_text', 'after_text']))
        # Paths to write working text, working pdf, and final output pdf.
        working_tex, working_pdf = map(basename_maker, ['.tex', '.pdf'])
        workpaths = working_tex, working_pdf, outputname

        nt = namedtuple('Paths', ['inputpaths', 'textwraps', 'workfiles'])
        return nt(parsepaths, texts, workpaths)

    def __init__(self):
        pass

    @classmethod
    def _get_args(cls, inputpath, outname=None, standalone=False):
        inputpath = Path(inputpath)
        basename = inputpath.namebase
        curdir = Path(inputpath.dirname() or os.curdir)
        update_config(curdir)
        dirs = ['resources', config['workdir']]
        resource_dir, work_dir = map(curdir.joinpath, dirs)
        if not work_dir.exists():
            work_dir.mkdir()
        args = [work_dir, resource_dir, standalone,
                basename, config['resources']]

        def basename_maker(ext):
            return work_dir.joinpath(basename + ext)

        resource_maker = partial(cls._process_resource, *args)
        outname = outname or basename + '.pdf'
        return inputpath, outname, resource_maker, basename_maker

    @staticmethod
    def _process_resource(work_dir, resource_dir, standalone,
                          basename, resources, resource_name):
        resource = resources[resource_name]

        def _write_resource(name, text):
            path = work_dir.joinpath(name)
            path.write_text(text)
            return path

        def _read_resource(resource):
            z = map(resource.get, ['name', 'required', 'subst'])
            name, required, subst = z
            name = name or basename + resource['ext']

            def _read_substitute():
                sub_include = resource.get('sub_include')
                if not sub_include or standalone:
                    return subst
                _sub = {'name': sub_include['name'],
                        'subst': sub_include.get('subst') or ''}
                r = _read_resource(_sub)
                w = _write_resource(*r)
                i = w.namebase if w else '%'
                include = '\\include{%s}' % i
                return subst % include

            try:
                text = resource_dir.joinpath(name).text()
            except FileNotFoundError as e:
                if required or subst in [None, False]:
                    raise e
                text = _read_substitute()
            return name, text

        name, text = _read_resource(resource)
        if resource.get('output') == 'read':
            return text
        return _write_resource(name, text)


class PersDict():

    def __new__(cls, path):

        p_tuple = namedtuple('Person',
                             ['xml_id', 'indexname',
                              'indexonly', 'description'])

        def _freeze(values):
            return p_tuple(*values)

        people = map(cls.Person, parser.parse(path).getroot().iter('{*}person'))
        d = {person.xml_id: person for person in people}
        for person in d.values():
            person.update(d)
        d = {xml_id: _freeze(person._values()) for xml_id, person in d.items()}
        return d

    def __init__(self):
        pass

    class Person():
        """A person."""

        def __init__(self, tag):
            self.xml_id = self._xml_id(tag)
            self.indexonly = self._indexonly(tag)
            i_and_d = self._indexname_and_description(tag)
            self.indexname, self.description = i_and_d

        def _values(self):
            return (self.xml_id, self.indexname,
                    self.indexonly, self.description)

        def update(self, persdict):
            """Update description by parsing using persdict."""
            description, trait = self.description
            if trait is not None:
                parser.transform_tree(trait, persdict, in_body=False)
            trait = self._stripstring(trait)
            self.description = description(trait)

        @staticmethod
        def _xml_id(tag):
            return tag.get('{%s}id' % config['xml_namespace'])

        @staticmethod
        def _indexonly(tag):
            iattr = tag.get('indexonly') in ['true', 'True']
            itag = tag.find('{*}indexonly') is not None
            return iattr or itag

        @classmethod
        def _indexname_and_description(cls, tag):
            descript_fmt = '{} ({}--{}) {}'.format
            stripstring = cls._stripstring

            def _find_string(parent, query):
                tags = parent.iter('{*}' + query)
                matches = (stripstring(m) for m in tags)
                return ' '.join(matches)

            finder = partial(_find_string, tag.find('{*}persName'))
            nametags = ['forename', 'addName', 'surname']
            firstnames, addnames, surnames = map(finder, nametags)
            addnames = "`%s'" % addnames if addnames else ''
            all_names = [' '.join([firstnames, addnames]), surnames]
            indexname = ', '.join(reversed(all_names)).strip()
            name = ' '.join(all_names).strip()

            date_finder = partial(_find_string, tag)
            date_targets = ['birth', 'death']
            dates = map(date_finder, date_targets)

            descript_part = partial(descript_fmt, name, *dates)
            trait_tag = tag.find('{*}trait')
            return indexname, (descript_part, trait_tag)

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
