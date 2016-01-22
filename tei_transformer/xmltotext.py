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

    def __init__(self, working_directory, parser):
        self.picklepath = os.path.join(working_directory, 'personlist.pickle')
        self.path = os.path.join(working_directory, 'personlist.xml')
        self.parser = parser
        self._get_persdict()

    def _get_persdict(self):
        nelson = self._from_pickle()
        if nelson:
            super().__init__(nelson)
        else:
            torpedoes = self._make_persdict()
            super().__init__(torpedoes)
            self._to_pickle()

    def _make_persdict(self):
        people = self.parser(self.path).getroot().iter('{*}person')
        return self._process_people(people)

    def _process_people(self, people):
        persdict = dict()
        for person in people:
            xml_id, person_dict = self._first_run(person)
            persdict[xml_id] = person_dict
        return self._second_run(persdict)

    # PROCESSING TAGS

    def _first_run(self, tag):
        person = dict()
        xml_id = self._xml_id(tag)
        person['indexname'] = self._indexname(tag)
        person['description'] = tag
        return xml_id, person

    def _second_run(self, persdict):
        for xml_id, person in persdict.items():
            tag = person['description']
            person['indexonly'] = self._indexonly(tag)
            person['description'] = self._get_description(tag, persdict)
        return persdict


    # INFO FROM TAGS

    def _xml_id(self, tag):
        return tag.attrib.get('%sid' % '{http://www.w3.org/XML/1998/namespace}')

    def _indexname(self, tag):
        firstnames, surnames = self.__get_names(tag)
        return ', '.join([' '.join(reversed(surnames)), firstnames])

    def _indexonly(self, tag):
        return tag.find('{*}indexonly') is not None # Non-TEI addition

    def _get_description(self, tag, persdict):
        name = self._descriptionname(tag)
        dates = self._dates(tag)
        biography = self._biography(tag, persdict)
        return ' '.join([name, dates, biography]).strip()

    # Getting description...

    def _descriptionname(self, tag):
        firstnames, surnames = self.__get_names(tag)
        surnames = ' '.join(surnames)
        return ' '.join([firstnames, surnames])

    def _dates(self, tag):
        birth = self.__find_string(tag, 'birth')
        death = self.__find_string(tag, 'death')
        return '(%s--%s)' % (birth[0], death[0])

    def _biography(self, tag, persdict):
        trait = tag.find('{*}trait')
        if trait is None:
            return ''
        traitpara = trait.find('{*}p')
        if traitpara is not None:
            if traitpara.getchildren() or traitpara.text:
                self.parser.transform_tree(traitpara, persdict, in_body=False)
                return traitpara.text.strip()
        return ''

    def __find_string(self, parent, searchterm):
        searchstring = '{*}' + searchterm
        matches = parent.findall(searchstring)
        return [str((name.text or '').strip()) for name in matches]

    def __get_names(self, tag):
        persname = tag.find('{*}persName')
        forenames = self.__find_string(persname, 'forename')
        addnames = ["`%s'" % x for x in self.__find_string(persname, 'addName')]
        surnames = self.__find_string(persname, 'surname')
        firstnames = ' '.join(forenames + addnames)
        return firstnames, surnames


    # PICKLING

    def _from_pickle(self):
        try:
            with open(self.picklepath, 'rb') as p:
                return pickle.load(p)
        except (EOFError, FileNotFoundError) as e:
            if e == EOFError: # i.e. something went wrong with pickling
                os.unlink(self.picklepath)

    def _to_pickle(self):
        with open(self.picklepath, 'wb') as p:
            pickle.dump(self.data, p)



class Parser():

    def __init__(self):
        lookup = etree.ElementNamespaceClassLookup()
        self.parser = etree.XMLParser(ns_clean=True, remove_comments=True, remove_blank_text=True)
        self.parser.set_element_class_lookup(lookup)
        namespace = lookup.get_namespace('http://www.tei-c.org/ns/1.0')
        # We set TEITag as the default class for the parser.
        namespace[None] = TEITag
        # Map the target to handling class in the lxml parser.
        for cls in self.tag_classes():
            namespace[cls.target] = cls

    def __call__(self, textpath):
        try:
            tree = etree.parse(textpath, self.parser)
        except FileNotFoundError:
            print('Could not find %s.' % textpath)
            sys.exit(1)
        except etree.XMLSyntaxError as err:
            print('An error occurred parsing {textpath}:\n\'{err}\''.format(textpath=textpath, err=err))
            sys.exit(1)
        return tree

    def _tag_classes(self, cls=TEITag):
        for subcls in cls.__subclasses__():
            yield from self._tag_classes(cls=subcls)
            if hasattr(subcls, 'target') and subcls.target:
                yield subcls


    def tag_classes(self):
        """You may well want to override this to include your own..."""
        return self._tag_classes()


    def transform_tree(self, tree, persdict, in_body=True):
        taglist = list(tree.getiterator('*'))
        taglist.sort(key=lambda tag: tag.descendants_count())
        for tag in taglist:
            if tag.localname == 'persName':
                if not in_body:
                    tag.process(persdict, in_body=False)
                else:
                    tag.process(persdict)
            else:
                tag.process()
        return tree 

