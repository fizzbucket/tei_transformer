import collections


class PersDict(collections.UserDict):

    """Create a persdict option used for identifying people in the text.
    Has keys made up of unique identifiers;
    these return a dictionary containing three values:
    1) 'indexname':
        the name used in indexing a person.
        This is a string [surnames], [firstnames].
    2) 'description':
        a description of a person suitable for use in a lemma note.
        This is a string [firstnames][surnames]([birth]-[death])[description]
    3) 'indexonly':
        a toggle for whether such a description should be used.

    We get this by parsing a file called, by default, 'personlist.xml'.
    This file should be made up of an xml-formatted list of people;
    see PersonInterpreter
    for how this should be formatted.
    """

    def __init__(self, path, parser):
        self.path = path
        self.parser = parser
        self._get_persdict()

    def _get_persdict(self):
        super().__init__()
        self._make_persdict()

    def _make_persdict(self):
        """Make persdict from path"""
        people = self.parser(self.path).getroot().iter('{*}person')
        people = [PersonMaker(person, self.parser) for person in people]

        for person in people:
            xml_id, person_struct = person.first_run()
            self.data[xml_id] = person_struct

        for person in people:
            self.data[person.xml_id] = person.second_run(self.data)


class PersonMaker():

    def __init__(self, tag, parser):
        self.tag = tag
        self.xml_id = self._xml_id()
        firstnames, surnames = self._get_names()
        self.firstnames = ' '.join(firstnames)
        self.reversed_surnames = ' '.join(reversed(surnames))
        self.surnames = ' '.join(surnames)
        self.parser = parser
        nt_list = ['indexname', 'indexonly', 'description']
        self.perstuple = collections.namedtuple(self.xml_id, nt_list)

    def first_run(self):
        self.indexname = self._indexname()
        return self.xml_id, self.perstuple(self.indexname, None, None)

    def second_run(self, persdict):
        indexonly = self._indexonly()
        description = self._get_description(persdict)
        empty = description == ''
        not_none = description is not None and not description == 'None'
        assert not_none or empty
        return self.perstuple(self.indexname, indexonly, description)

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
        if self.tag.find('{*}indexonly') is not None:  # Non-TEI addition
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

        self.parser.transform_tree(trait, persdict, in_body=False)
        if trait.text:
            return trait.text.strip()
        return ''

    @staticmethod
    def _find_string(parent, searchterm):
        """Return a string containing the text
        for each tag searchterm matches."""
        searchstring = '{*}' + searchterm
        matches = parent.findall(searchstring)
        return [str((name.text or '').strip()) for name in matches]
