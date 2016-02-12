from functools import partial
from .parser import Parser

def persdict(path):
    people = map(Person, Parser(path).getroot().iter('{*}person'))
    persdict = {person.xml_id: person for person in people}
    for person in persdict.values():
        person.update(persdict)
    return persdict


class Person():

    def __init__(self, tag):
        self.indexname, descript_name = self._names(tag)
        self.xml_id = tag.get('{http://www.w3.org/XML/1998/namespace}id')
        self.indexonly = self._indexonly(tag)
        self.description = self._description(tag, descript_name)

    def update(self, persdict):
        description, trait = self.description
        if trait is not None:
            transform_tree(trait, persdict, in_body=False)
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
        return ', '.join(reversed(all_names)), ' '.join(all_names)

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