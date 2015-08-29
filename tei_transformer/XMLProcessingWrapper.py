import re
import os
from operator import itemgetter
import sys
import pickle
import inspect
from lxml import etree

from .teitag import TEITag
from .importer import config, custom_teitag


def xml_to_tex(filepath, working_directory=None, persdict=None):
    if persdict:
        persdict = get_persdict(working_directory)
    processor = XMLProcessing()
    return processor.transform(filepath, persdict)

class XMLProcessing():

    def __init__(self):
        #self.var_adder = AddVariables()
        self.persdict = None

    def transform(self, textpath, persdict):
        tree = self.open_and_parse(textpath)
        root = tree.getroot()
        body = root.find('.//{*}body') # {*} is to map any namespace
        assert body is not None
        text, definitions = self.un_xml(body, persdict)
        return self.latexify(text, definitions)

    @staticmethod
    def latexify(text, definitions):
        """Add a latex preface and ending"""
        front_stuff = '\n'.join(['\n', definitions, config.latex_front_matter()])
        header = config.latex_preamble().replace(r'\begin{document}', front_stuff)
        endstatement = config.latex_back_matter()
        return '\n'.join([header, text, endstatement])

    @staticmethod
    def open_and_parse(textpath):

        lookup = etree.ElementNamespaceClassLookup()
        parser = etree.XMLParser(ns_clean=True, remove_comments=True, remove_blank_text=True)
        parser.set_element_class_lookup(lookup)
        namespace = lookup.get_namespace('http://www.tei-c.org/ns/1.0')
        # We set TEITag as the default class for the parser.
        namespace[None] = TEITag
        # Each subclass of TEITag and its target is then identified.
        subclasses = []
        subclasstargets = []
        try:
            custom_members = inspect.getmembers(custom_teitag, inspect.isclass)
        except NameError: # i.e not imported, because it didn't exist.
            custom_members = list()
        for classname, cls in custom_members:
            if issubclass(cls, TEITag) and not cls.__name__ == 'TEITag':
                subclasses.append(cls)
                subclasstargets.append(cls.target)
                print('Tags of type `%s\' are being handled by a custom class.' % cls.target)

        for cls in TEITag.__subclasses__():
            # We want not to override custom classes.
            if cls.target not in subclasstargets:
                subclasses.append(cls)
                subclasstargets.append(cls.target)

        # Map the target to handling class in the lxml parser.
        for cls in subclasses:
            namespace[cls.target] = cls

        try:
            tree = etree.parse(textpath, parser)
        except OSError:
            print('Could not find %s.' % textpath)
            sys.exit(1)
        except etree.XMLSyntaxError as err:
            print('An error occurred parsing {textpath}:\n\'{err}\''.format(textpath=textpath, err=err))
            sys.exit(1)
        return tree

    def un_xml(self, tree, persdict):
        self.definitions = list()
        self.taglen = 0
        if not self.persdict and persdict:
            self.persdict = persdict
        self.numprocessed = 0
        
        self.process_tree(tree)

        #outtext = tree.text.strip()
        # Shouldn't be necessary...
        outtext = '\n'.join(tree.itertext()).strip()
        outtext = self.clean_up(outtext)
        defstring = '\n'.join(self.definitions)
        return outtext, defstring


    def process_tree(self, tree):

        taglist = list(tree.getiterator('*'))
        # We need to do this before the order is shuffled.
        # But it has to be while the original taglist is still alive,
        # so that a new Python representation is not created later on,
        # which would override our changes.
        for tag in taglist:
            if self.persdict:
                if tag.localname == 'persName':
                    tag.preprocess(self.persdict)
            else:
                tag.no_persdict = True

        taglist.sort(key=lambda tag: tag.number_of_descendants)

        for tag in taglist:
            self.process_tag(tag)

    def process_tag(self, newtag):

        replacement = newtag.replacement

        if replacement is None:
            pass
        else:
            newtag.replace_with(replacement)

            if newtag.localname == 'note' and newtag.defstring:
                self.definitions.append(newtag.defstring)


    def clean_up(self, text):
        
        text = self.fix_hyphens(text)
        for original, new in config.custom_string_replacements().items():
            text = text.replace(original, new)
        text = text.replace('----)', '--)')
        text = re.sub(r'\ +', ' ', text) # Be a tidy kiwi.
        text = re.sub(r'\n\ +', '\n', text)
        text = re.sub(r'\n\n+', '\n\n', text)
        return text


    def fix_hyphens(self, text):

        for char in '.,!)':
            text = text.replace('-' + char, '---' + char)

        hyphensubs = [(r'(?<=\d)-(?=\d)', '--'), # hyphens between numbers to en-dashes
                    (r'(?<=\s)-(?=\s)', '---'), # hyphens surrounded by whitespace to em-dashes.
                    ]

        for sub in hyphensubs:
            text = re.sub(sub[0], sub[1], text)

        # Hyphens in our citations!
        text = re.sub(r'\\pageref\{(.*?)--(.*?)\}',
            r'\\pageref{\1-\2}', text)
        text = re.sub(r'\\autocite\{(.*?)--(.*?)\}',
            r'\\autocite{\1-\2}', text)
        text = re.sub(r'\\label\{(.*?)--(.*?)\}',
            r'\\label{\1-\2}', text)

        return text

def get_persdict(workdir):
    picklepath = os.path.join(workdir, 'personlist.pickle')
    if os.path.isfile(picklepath):
        with open(picklepath, 'rb') as perspickle:
            try:
                persdict = pickle.load(perspickle)
                return persdict
            except EOFError: # If something went wrong w pickling.
                os.unlink(picklepath)
    persdict = PersDict(workdir)
    persdict = persdict.processor()
    
    with open(picklepath, 'wb') as perspickle:
        pickle.dump(persdict, perspickle)
    return persdict

class PersDict():

    """Class defining a dictionary of people to be used in later processing."""

    def __init__(self, workdir):
        self.xmlpath = os.path.join(workdir, 'personlist.xml')
        if not os.path.exists(self.xmlpath):
            print('Could not find persName list.')
            print('Expected location was %s' % self.xmlpath)
            sys.exit(2)
        xml_class = XMLProcessing()

    def processor(self):
        people = self.get_xml_people()
        people = [Person(x) for x in people]
        persdict = dict()
        for person in people:
            persdict[person.xml_id] = dict()
            persdict[person.xml_id]['indexname'] = person.indexname
        for person in people:
            persdict[person.xml_id]['replacephrase'] = person.get_replace_phrase(persdict)
            persdict[person.xml_id]['persname_used'] = False
            persdict[person.xml_id]['indexing_only'] = person.indexing_only
        return persdict

    def get_xml_people(self):
        tree = XMLProcessing.open_and_parse(self.xmlpath)
        root = tree.getroot()
        return root.iter('{*}person')

class Person():

    """Class defining a person"""

    def __init__(self, tag):
        self.xml_id = self.get_xml_id(tag.attrib)
        self.indexname, self.descriptionname = self.get_names(tag)
        self.dates = self.get_dates(tag)
        self.description_tags = self.get_description_tags(tag)
        self.indexing_only = self.only_index(tag)
        
    def get_xml_id(self, attribs):
        for attrib in attribs:
            if attrib.split('}')[1] == 'id':
                return attribs[attrib]

    def only_index(self, tag):
        if tag.find('{*}indexonly') is not None: # Non-TEI addition
            return True
        else:
            return False

    def get_names(self, tag):
        persname = tag.find('{*}persName')
        forenames = self.stringify(persname, 'forename')
        addnames = self.stringify(persname, 'addName')
        addnames = map(lambda name: "`%s'" % name, addnames)
        surnames = self.stringify(persname, 'surname')
        surnames = list(surnames)

        firstnames = list(forenames) + list(addnames)
        firstnames = ' '.join(firstnames)

        indexname = ', '.join([' '.join(reversed(surnames)), firstnames])
        descriptionname = ' '.join([firstnames, ' '.join(surnames)])
        return indexname, descriptionname

    @staticmethod
    def stringify(parent, desired):
        searchstring = '{*}' + desired
        namelist = parent.findall(searchstring)
        return map(lambda name: str((name.text or '').strip()), namelist)

    def dateify(self, parent, desired):
        date = self.stringify(parent, desired)
        date = next(date)
        if date == '':
            date == '????'
        elif date.lower() == 'alive':
            date = ' '
        return date

    def get_dates(self, tag):
        birth = self.dateify(tag, 'birth')
        death = self.dateify(tag, 'death')
        return ' (%s--%s) ' % (birth, death)

    def get_description_tags(self, tag):
        trait = tag.find('{*}trait')
        if trait is not None:
            traitpara = trait.find('{*}p')
            if traitpara is not None:
                if traitpara.getchildren() or traitpara.text:
                    return traitpara
        return False

    def get_replace_phrase(self, persdict):

        description = self.get_description(persdict)

        replacephrase = '{{{name}{dates}{description}}}'

        return replacephrase.format(name=self.descriptionname,
                                    dates=self.dates,
                                    description=description,)
        

    def get_description(self, persdict):
        if self.description_tags is False:
            return str()
        
        description_tags = list(self.description_tags.iter())
        description_tags.sort(key=lambda tag: tag.number_of_descendants)
        for tag in description_tags:
            if tag.localname == 'persName':
                tag.is_body_text = False
                tag.preprocess(persdict)
            replacement = tag.replacement
            if replacement:
                tag.replace_with(replacement)
        description = self.description_tags.text
        description = re.sub(r'\s+', ' ', str(description))

        nospacebefores = ',.;\''
        nospaceafters = '`'
        chars = [' %s' % char for char in nospacebefores] + \
                ['%s ' % char for char in nospaceafters]
        for char in chars:
            description = description.replace(char, char.strip())
        description = re.sub(r',(?=\S)', ', ', description)
        if description == 'None':
            return str()
        return description.strip()