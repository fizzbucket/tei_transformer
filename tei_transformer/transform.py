"""Transform a tei file."""

import argparse
import os
import re
import subprocess
import sys
from collections import namedtuple
from functools import partial

from lxml import etree
from path import Path

from .tags import TEITag
from .config import config, update_config


class ParserMethods():
    """Methods for parsing and transforming XML."""

    @staticmethod
    def transform_tree(tree, persdict, in_body=True):
        """Transform a tree."""
        for tag in sorted(list(tree.getiterator('*'))):
            if tag.localname == 'persName':
                tag.process(persdict, in_body=in_body)
            else:
                tag.process()
        return tree

    @classmethod
    def parser(cls):
        """Create a parser with custom tag handling."""
        parser = etree.XMLParser(**config['parser_options'])
        lookup = etree.ElementNamespaceClassLookup()
        parser.set_element_class_lookup(lookup)
        namespace = lookup.get_namespace('http://www.tei-c.org/ns/1.0')
        namespace[None] = TEITag

        def _handlers(target_class):
            for subcls in target_class.__subclasses__():
                yield from _handlers(subcls)
                if hasattr(subcls, 'targets') and subcls.targets:
                    for target in subcls.targets:
                        yield subcls, target

        for handler, target in _handlers(TEITag):
            namespace[target] = handler
        return parser

    @classmethod
    def parse(cls, textpath):
        """Parse textpath"""
        return etree.parse(textpath, cls.parser())


class Transformer(ParserMethods):

    """Transform inputname, latexify the text produced, and make a pdf"""

    def __init__(self, inputname, outputname=None,
                 force=False, standalone=False):
        resources = self.Resources(inputname, outputname, standalone)
        bare_text = self.transform(*resources.inputpaths)
        latex = self.latexify(bare_text, *resources.textwraps)
        self.make_pdf(latex, force, *resources.workfiles)

    def transform(self, inputpath, personlistpath):
        body = self.parse(inputpath).getroot().find('.//{*}body')
        assert body is not None
        tree = self.transform_tree(body, PersDict(personlistpath))
        return '\n'.join(tree.itertext()).strip()

    @staticmethod
    def latexify(bare_text, before, after):
        text = '\n'.join([before, bare_text, after])
        for fix in config['string_replacements']:
            text = text.replace(*fix)
        for fix in config['regex_replacements']:
            text = re.sub(fix[0], fix[1], text)
        return text

    @staticmethod
    def make_pdf(latex, force, working_tex, working_pdf, out_pdf):
        missing = not working_pdf.exists() or not working_tex.exists()
        if force or missing or hash(working_tex.text()) != hash(latex):
            working_tex.write_text(latex)
            call_cmd = config['caller_command']
            latexmk = '{c} {w}'.format(c=call_cmd, w=working_tex).split()
            subprocess.call(latexmk)
        working_pdf.copy(out_pdf)

    class Resources():

        def __new__(cls, *args, **kwargs):
            inputpath, outputname, resource_maker, basename_maker = \
                cls._get_args(*args, **kwargs)

            classifications = config['resource_classifications']
            resources = {k: [resource_maker(r) for r in v] for k, v
                         in classifications.items()}

            def groups(target):
                return iter(resources[target])

            parsepaths = inputpath, next(groups('parsepath'))
            texts = map('\n'.join, map(groups, ['before_text', 'after_text']))
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


class PersDict(ParserMethods):

    def __new__(cls, path):

        p_tuple = namedtuple('Person',
                             ['xml_id', 'indexname',
                              'indexonly', 'description'])

        def _freeze(values):
            return p_tuple(*values)

        people = map(cls.Person, cls.parse(path).getroot().iter('{*}person'))
        d = {person.xml_id: person for person in people}
        for person in d.values():
            person.update(d)
        d = {xml_id: _freeze(person._values()) for xml_id, person in d.items()}
        return d

    def __init__(self):
        pass

    class Person(ParserMethods):
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
                self.transform_tree(trait, persdict, in_body=False)
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
            targets = ['forename', 'addName', 'surname']
            firstnames, addnames, surnames = map(finder, targets)
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
    args = vars(parser.parse_args(sys.argv[1:]))
    Transformer(args.pop('inputname'), **args)


if __name__ == '__main__':
    main()
