import os
import sys
import pickle
from lxml import etree

import collections

from .tags import TEITag

class Transform():

    def __init__(self, filepath, working_directory, use_persdict=True):

        self.filepath = filepath
        self.working_directory = working_directory

        self.parser = Parser()
        if use_persdict:
            self.persdict = PersDict(self.working_directory, self.parser)
        else:
            self.persdict = None

    def transform(self):
        tree = self.parser(self.filepath)
        root = tree.getroot()
        body = root.find('.//{*}body') # {*} is to map any namespace
        assert body is not None
        tree = self.parser.transform_tree(body, self.persdict)
        return '\n'.join(tree.itertext()).strip()

class PersDict(collections.UserDict):

    """Create a persdict option used for identifying people in the text.
    Has keys made up of unique identifiers; these return a dictionary containing three values:
    1) 'indexname': the name used in indexing a person.
        This is a string [surnames], [firstnames].
    2) 'description': a description of a person suitable for use in a lemma note.
        This is a string [firstnames][surnames]([birth]-[death])[description]
    3) 'indexonly': a toggle for whether such a description should be used.

    We get this by parsing a file called, by default, 'personlist.xml'.
    This file should be made up of an xml-formatted list of people; see PersonInterpreter
    for how this should be formatted.
    """

    def __init__(self, working_directory, parser, filename="personlist.xml"):
        self.picklepath = os.path.join(working_directory, 'personlist.pickle')
        self.path = os.path.join(working_directory, filename)
        self.parser = parser
        self._get_persdict()

    def _get_persdict(self):
        """Wrapper to either
        load persdict from pickled version from last run
        or make anew"""
        nelson = self._from_pickle()
        if nelson:
            super().__init__(nelson)
        else:
            super().__init__()
            self._make_persdict()
            self._to_pickle()

    def _make_persdict(self):
        """Make persdict from path"""
        people = self.parser(self.path).getroot().iter('{*}person')
        people = [PersonMaker(person, self.parser) for person in people]

        for person in people:
            xml_id, person_dict = person.first_run()
            self.data[xml_id] = person_dict

        for person in people:
            person.second_run(self.data)
        

    def _from_pickle(self):
        """Load persdict from pickle"""
        try:
            with open(self.picklepath, 'rb') as p:
                return pickle.load(p)
        except (EOFError, FileNotFoundError) as e:
            if e == EOFError: # i.e. something went wrong with pickling
                os.unlink(self.picklepath)

    def _to_pickle(self):
        """Dump persdict to pickle"""
        with open(self.picklepath, 'wb') as p:
            pickle.dump(self.data, p)


class PersonMaker(collections.UserDict):

    def __init__(self, tag, parser):
        super().__init__()
        self.tag = tag
        self.xml_id = self._xml_id()
        firstnames, surnames = self._get_names()
        self.firstnames = ' '.join(firstnames)
        self.reversed_surnames = ' '.join(reversed(surnames))
        self.surnames = ' '.join(surnames)
        self.parser = parser

    def first_run(self):
        self.data['indexname'] = self._indexname()
        return self.xml_id, self.data

    def second_run(self, persdict):
        self.data['indexonly'] = self._indexonly()
        self.data['description'] = self._get_description(persdict)

    def _indexname(self):
        return ', '.join([self.reversed_surnames, self.firstnames])

    def _xml_id(self):
        ns = '{http://www.w3.org/XML/1998/namespace}'
        attrib = self.tag.attrib
        return attrib.get('%sid' % ns)

    def _get_names(self):
        """Firstnames and surnames from person"""
        persname = self.tag.find('{*}persName')
        forenames = self._find_string(persname, 'forename')
        addnames = ["`%s'" % x for x in self._find_string(persname, 'addName')]
        surnames = self._find_string(persname, 'surname')
        firstnames = forenames + addnames
        return firstnames, surnames

    def _indexonly(self):
        if self.tag.find('{*}indexonly') is not None: # Non-TEI addition
            return True
        else:
            return self.tag.get('indexonly') in ['true', 'True']

    def _get_description(self, persdict):
        name = self._descriptionname()
        dates = self._dates()
        biography = self._biography(persdict)
        return ' '.join([name, dates, biography]).strip()

    # Getting description...

    def _descriptionname(self):
        return ' '.join([self.firstnames, self.surnames])

    def _dates(self):
        birth = self._find_string(self.tag, 'birth')
        death = self._find_string(self.tag, 'death')
        return '(%s--%s)' % (birth[0], death[0])

    def _biography(self, persdict):
        """Biography from person"""
        trait = self.tag.find('{*}trait')
        if trait is None:
            return ''
        traitpara = trait.find('{*}p')
        if traitpara is not None:
            if traitpara.getchildren() or traitpara.text:
                self.parser.transform_tree(traitpara, persdict, in_body=False)
                return traitpara.text.strip()
        return ''

    @staticmethod
    def _find_string(parent, searchterm):
        """Return a string containing the text for each tag searchterm matches."""
        searchstring = '{*}' + searchterm
        matches = parent.findall(searchstring)
        return [str((name.text or '').strip()) for name in matches]


class Parser():

    """Parser and configuration options"""

    def __init__(self):
        lookup = etree.ElementNamespaceClassLookup()
        self.parser = etree.XMLParser(**self.parser_options())
        self.parser.set_element_class_lookup(lookup)
        namespace = lookup.get_namespace('http://www.tei-c.org/ns/1.0')
        # We set TEITag as the default class for the parser.
        namespace[None] = self.base_tag_class()
        # Map the target to handling class in the lxml parser.
        for cls in self.tag_classes():
            if isinstance(cls.target, list):
                for target in cls.target:
                    namespace[target] = cls
            else:
                namespace[cls.target] = cls

    def __call__(self, textpath):
        """Parse textpath and return it"""
        try:
            tree = etree.parse(textpath, self.parser)
        except FileNotFoundError:
            print('Could not find %s.' % textpath)
            sys.exit(1)
        except etree.XMLSyntaxError as err:
            print('An error occurred parsing {textpath}:\n\'{err}\''.format(textpath=textpath, err=err))
            sys.exit(1)
        return tree


    def parser_options(self):
        """Options for lxml parser"""
        return {'ns_clean': True,
                'remove_comments':True,
                'remove_blank_text':True}

    def tag_classes(self):
        """Return classes to handle tags.
        You may well want to override this to include your own..."""
        return self._tag_classes()

    def base_tag_class(self):
        """Return the default class to handle tags"""
        return TEITag

    def _tag_classes(self, cls=TEITag):
        for subcls in cls.__subclasses__():
            yield from self._tag_classes(cls=subcls)
            if hasattr(subcls, 'target') and subcls.target:
                yield subcls



    def transform_tree(self, tree, persdict, in_body=True):
        """Transform a tree"""
        # Using a heap here would be slower
        tags = list(tree.getiterator('*'))
        tags.sort()
        for tag in tags:
            if tag.localname == 'persName':
                if not in_body:
                    tag.process(persdict, in_body=False)
                else:
                    tag.process(persdict)
            else:
                tag.process()
        return tree 

