import subprocess
import re
import os
from functools import partial
from itertools import chain
from collections import UserDict, namedtuple
import argparse
import sys

from lxml import etree
from path import Path

from .config import config, update_config
from .tags import TEITag

class Parser():

    """An instance of etree.XMLParser using custom taghandlers.

    These handlers are derived from those subclasses of TEITag
    which have an attribute 'targets'. Each tag the parser finds
    which matches these targets will be handled by the subclass.
    """

    def __new__(cls):
        return cls._make_parser()

    def __init__(self):
        pass
    
    @classmethod
    def _make_parser(cls):
        parser = etree.XMLParser(**config['parser_options'])
        lookup = etree.ElementNamespaceClassLookup()
        parser.set_element_class_lookup(lookup)
        namespace = lookup.get_namespace('http://www.tei-c.org/ns/1.0')
        namespace[None] = TEITag
        for handler, target in cls._handlers(TEITag):
            namespace[target] = handler
        return parser
    
    @classmethod
    def _handlers(cls, target_class):
        """Yield a tuple of descendant and target for each target
        listed in descendant.targets for each descendant of target_class"""
        for subcls in target_class.__subclasses__():
            yield from cls._handlers(subcls)
            if hasattr(subcls, 'targets') and subcls.targets:
                for target in subcls.targets:
                    yield subcls, target


class ParserMethods():

    """Methods for parsing and transforming XML."""

    @staticmethod
    def transform_tree(tree, persdict, in_body=True):
        """Transform a tree.

        A list of each tag in tree is first weakly sorted by number of children.
        Then each tag will have its :method:`process` called.

        If the tag is of type 'persName', :param:`persdict` and :param:`in_body`
        will be used as arguments to :method:`process`.

        :param tree: A parsed tree.
        :param arg2: A dictionary of people
        :type tree: TEITag
        :type persdict: PersDict
        :return: The processed tree; likely to be a single tag.
        :rtype: TEITag
        :keyword in_body: whether the tree is in body text or not.
        :type in_body: bool
        """
        for tag in sorted(list(tree.getiterator('*'))):
            if tag.localname == 'persName':
                tag.process(persdict, in_body=in_body)
            else:
                tag.process()
        return tree

    @staticmethod
    def parse(textpath, parser=Parser()):
        return etree.parse(textpath, parser)


class Transformer(ParserMethods):

    """Transform inputname, latexify the text produced, and make a pdf"""

    def __init__(self, inputname, outputname=None,
        force=False, standalone=False):
        paths = Paths(inputname, outputname, standalone)
        bare_text = self.transform(*paths.inputpaths)
        latex = self.latexify(bare_text, *paths.textwraps)
        self.make_pdf(latex, force, *paths.workfiles)

    def transform(self, inputpath, personlistpath):
        """Transform :param:`inputpath` to text."""
        body = self.parse(inputpath).getroot().find('.//{*}body')
        assert body is not None
        tree = self.transform_tree(body, PersDict(personlistpath))
        return '\n'.join(tree.itertext()).strip()

    @staticmethod
    def latexify(bare_text, before, after):
        """"Wrap :param:`bare_text` with :param:`before` and :param:`after.
        Return this text with string replacements and regex replacements applied"""
        text = '\n'.join([before, bare_text, after])
        for fix in config['string_replacements']:
            text = text.replace(*fix)
        for fix in config['regex_replacements']:
            text = re.sub(*fix, text)
        return text

    @staticmethod
    def make_pdf(latex, force, working_tex, working_pdf, out_pdf):
        """Make a pdf from :param:`latex`."""
        missing = not working_pdf.exists() or not working_tex.exists()
        if force or missing or hash(working_tex.text()) != hash(latex):
            working_tex.write_text(latex)
            call_cmd = config['caller_command']
            latexmk = '{c} {w}'.format(c=call_cmd, w=working_tex).split()
            subprocess.call(latexmk)
        working_pdf.copy(out_pdf)


class PersDict(UserDict, ParserMethods):

    def __init__(self, path):
        people = map(self.Person, self.parse(path).getroot().iter('{*}person'))
        self.data = {person.xml_id: person for person in people}
        for person in self.data.values():
            person.update(self.data)

    class Person(ParserMethods):

        def __init__(self, tag):
            self.indexname, descript_name = self._names(tag)
            self.xml_id = tag.get('{http://www.w3.org/XML/1998/namespace}id')
            self.indexonly = self._indexonly(tag)
            self.description = self._description(tag, descript_name)

        def update(self, persdict):
            description, trait = self.description
            if trait is not None:
                self.transform_tree(trait, persdict, in_body=False)
            self.description = description(self._stripstring(trait))

        @staticmethod
        def _indexonly(tag):
            iattr = tag.get('indexonly') in ['true', 'True']
            itag = tag.find('{*}indexonly') is not None
            return iattr or itag

        @classmethod
        def _names(cls, tag):
            finder = partial(cls._find_string, tag.find('{*}persName'))
            targets = ['forename', 'addName', 'surname']
            firstnames, addnames, surnames = map(finder, targets)
            addnames = "`%s'" % addnames if addnames else ''
            all_names = [' '.join([firstnames, addnames]), surnames]
            return ', '.join(reversed(all_names)).strip(), ' '.join(all_names).strip()

        @classmethod
        def _dates(cls, tag):
            date_finder = partial(cls._find_string, tag)
            date_targets = ['birth', 'death']
            return map(date_finder, date_targets)

        @classmethod
        def _description(cls, tag, name):
            descript_fmt = '{} ({}--{}) {}'.format
            descript_part = partial(descript_fmt, name, *cls._dates(tag))
            trait_tag = tag.find('{*}trait')
            return descript_part, trait_tag

        @staticmethod
        def _stripstring(tag):
            try:
                return str(tag.text).strip()
            except AttributeError:
                return ''

        @classmethod
        def _find_string(cls, parent, query):
            """Return a string concatenating the text
            in each tag searchterm matches."""
            matches = (cls._stripstring(m) for m in parent.iter('{*}' + query))
            return ' '.join(matches)


class Paths():

    def __new__(cls, *args, **kwargs):
        p = cls.PathManager(*args, **kwargs)
        c = namedtuple('Paths', ['inputpaths', 'textwraps', 'workfiles'])
        return c(*p.paths())

    def __init__(self):
        pass     

    class PathManager():

        def __init__(self, inputpath, outputname=None, standalone=False):
            self.inputpath = Path(inputpath)
            self.basename = self.inputpath.namebase
            self.outputname = outputname or self.basename + '.pdf'
            self.standalone = standalone
            self._dirs()

        def paths(self):
            references, indexstyle = self._process(['references', 'indexstyle'])
            return self.parsepaths(), self.textwraps(), self.workpaths()

        def parsepaths(self):
            return self.inputpath, next(self._process(['personlist']))

        def textwraps(self):
            before_text = ['preamble', 'after_preamble', 'after_text_start']
            after_text = ['after_text_end']
            return map('\n'.join, map(self._process, [before_text, after_text]))

        def workpaths(self):
            names = map(lambda ext: self.basename + ext, ['.tex', '.pdf'])
            working_tex, working_pdf = map(self.extend_workdir, names)
            return working_tex, working_pdf, self.outputname

        def _process(self, rnamelist):
            return map(self.process_resource, [config['resources'][x] for x in rnamelist])

        def _dirs(self):
            curdir = self.inputpath.dirname() or os.curdir
            update_config(curdir)
            curdir = Path(curdir)
            resource_dir = self._extend_dir(curdir, 'resources', required=True)
            work_dir = self._extend_dir(curdir, config['workdir'], make=True) 
            self.extend_resourcedir = partial(self._extend_dir, resource_dir)
            self.extend_workdir = partial(self._extend_dir, work_dir)

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
                text = r.text()
            except FileNotFoundError as e:
                if subst in [None, False]:
                    raise e
                text = self.process_subst(resource, subst)
            if resource.get('output') == 'read':
                return text
            w.write_text(text)
            return w

        def process_subst(self, resource, subst):
            sub_include = resource.get('sub_include')
            if sub_include and not self.standalone:
                _sub = {'name': sub_include['name'], 'subst': sub_include.get('subst') or ''}
                sub_include = self.process_resource(_sub)
                i = sub_include.namebase if sub_include else '%'
                include = '\\include{%s}' % i
                return subst % include
            return subst

class Caller():

    def __init__(self):
        argparser = self._parser()
        args = vars(argparser.parse_args(sys.argv[1:]))
        inputname = args.pop('inputname')
        Transformer(inputname, **args)

    @staticmethod
    def _parser():
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
        return parser

def main():
    Caller()

if __name__ == '__main__':
    main()

