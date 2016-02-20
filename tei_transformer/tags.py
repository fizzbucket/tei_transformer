import calendar
from functools import partial

from latexfixer.fix import LatexText

from lxml import etree

from .config import config
from .etreemethods import EtreeMethods


class ImplementationError(Exception):
    pass


class TEITag(etree.ElementBase, EtreeMethods):

    def _init(self):
        self.transform_text()

    def transform_text(self):
        if self.text:
            self.text = self._process_text_contents(self.text)
        if self.tail:
            self.tail = self._process_text_contents(self.tail)

    def process(self, persdict=None, in_body=True):

        # Check to see we won't accidentally wipe something out.
        not_good_children = self.localname not in ['choice', 'app']
        if not len(self) == 0 and not_good_children:
            self.raise_()
        # Now on with the replacement.
        if self.localname == 'persName':
            self.persdict = persdict
            self.in_body = in_body and self.in_body

        try:
            replacement = self.get_replacement()
        except (KeyError, AttributeError):
            self.raise_()
        # We don't want to catch an empty string,
        if replacement is None:
            return
        else:
            self.string_replace(replacement)

    def _process_text_contents(self, text):
        """Function called to manipulate text in tags or tail when first parsed.
        """
        return LatexText(text)

    def get_replacement(self):
        """Called to get a string replacement for a tag"""
        raise NotImplementedError(self)

    def raise_(self):
        """Raise an implementation error with self as argument"""
        raise ImplementationError(self)

    def _check_if_in_body(self):
        note_ancestors = self.iterancestors('{*}note')
        return not bool(any(True for _ in note_ancestors))


class Head(TEITag):

    targets = ['head']

    def get_replacement(self):
        """ Return the replacement for a tag of type <head>"""

        # Make explicit the desire not to indent following paragraph.
        if not self.tail or not self.tail.strip():
            next_sibling = self.getnext()
            if next_sibling is not None and next_sibling.localname == 'p':
                if not next_sibling.get('rend'):
                    t = next_sibling.text or ''
                    next_sibling.text = '\\noindent %s' % t

        parent_attrs = self.getparent().attrib
        div_type = parent_attrs['type']
        if div_type == 'title':  # Chapter
            return self.process_head_level_two()

        try:
            identifier = parent_attrs['{%s}id' % config['xml_namespace']]
        except KeyError:
            self.raise_()

        if div_type == 'diaryentry':  # Section
            return self.process_head_level_three(identifier)
        elif div_type == 'diaryentrysection':  # Subsection
            return self.process_head_level_four(identifier)
        self.raise_()

    def process_head_level_one(self):
        return '\\part{%s}' % self.text

    def process_head_level_two(self):
        return '\\pstart\n\\eledchapter*{%s}\n\\pend' % self.text

    def process_head_level_three(self, identifier):
        if not identifier:
            self.raise_()
        month = identifier[:3]
        # Assumes gregorian calendar
        for index, string in enumerate(calendar.month_abbr):
            if string == month:
                month = calendar.month_name[index]
                break
        date = identifier[3:identifier.find('_')]
        year = identifier[-4:]
        return '\n\\pstart\n\
               \\eledsection[%s %s %s]{%s}\n\
               \\label{%s}\n\
               \\pend'\
               % (date, month, year, self.text, identifier)

    def process_head_level_four(self, identifier):
        return '\\pstart\n\\eledsubsection{%s}\n\\label{%s}\n\\pend'\
            % (self.text, identifier)

    def process_head_level_five(self, identifier):
        return '\\pstart\n\\eledsubsubsection{%s}\n\\label{%s}\n\\pend'\
            % (self.text, identifier)


class TextualNote(TEITag):

    targets = ['note']

    def get_replacement(self):
        if self.empty():
            return

        marker = self.get_marker()
        if marker is False or self.get('type') != 'annotation':
            self.raise_()

        abbreviation = self.get('ln')
        if abbreviation:
            return self.abbreviated_lemma(marker, abbreviation)
        return self.unabbreviated_lemma(marker)

    def abbreviated_lemma(self, marker, abbreviation):
        marker.string_replace('\\annotationlem{')
        abbreviation = self._process_text_contents(abbreviation)
        return '}{%s}{%s}' % (abbreviation, self.text)

    def unabbreviated_lemma(self, marker):
        marker.string_replace('\\annotation{')
        return '}{%s}' % self.text

    def empty(self):
        return not self.text and len(self.getchildren()) == 0

    def get_marker(self):
        skip = 0
        for n in self.itersiblings('{*}note', preceding=True):
            if n.text:
                skip += 1
            else:
                if skip == 0:
                    return n
                skip = skip - 1
        return False


class Paragraph(TEITag):
    targets = ['p']

    def _init(self):
        super()._init()
        self._in_bio = None

    @property
    def in_bio(self):
        if not isinstance(self._in_bio, bool):
            self._in_bio = self.getparent().localname == 'trait'
        return self._in_bio

    def get_replacement(self):
        text = self.prepare_text()
        non_body = self.in_bio or not self._check_if_in_body()
        if non_body:
            return self._handle_non_body_para(text)
        return self._handle_body_para(text)

    def _handle_non_body_para(self, text):
        has_following = self.getnext() is not None or self.tail
        if not text or not has_following:
            return text
        return '%s\\par ' % text

    def _handle_body_para(self, text):
        rend = self.get('rend')
        if rend in ['noindent', 'indent', 'doubleindent']:
            indent = '\\' + rend
        elif self.after_header():
            # Our headers are wrapped in an eledmac paragraph.
            # So latex doesn't know not to indent them.
            indent = '\\noindent'
        else:
            indent = ''
        return ' '.join(['\n\\pstart', indent, text, '\\pend'])

    def prepare_text(self):
        try:
            return self.text.strip().replace('\n', ' ')
        except AttributeError:
            if self.in_bio: # ie don't necessarily need text
                return ''
            self.raise_()

    def after_header(self):
        previous = self.getprevious()
        try:
            head = previous.localname == 'head'
            tail = previous.tail and previous.tail.strip()
            if head and not tail:
                return True
        except AttributeError:
            pass


class VerseLineGroup(TEITag):
    targets = ['lg']

    def _init(self):
        super()._init()
        if self.tail:
            self.tail = self.tail.strip()

    def get_replacement(self):
        stanzatext = self.text.strip()
        stanzatext = stanzatext.rstrip('&')
        return '\n\n\\stanza\n%s \\&\n\n' % stanzatext


class VerseLine(TEITag):
    targets = ['l']

    def get_replacement(self):
        self.tail = self.tail.strip() if self.tail else ''
        self.text = self.text.strip() if self.text else ''
        return '%s &\n' % self.text


class Foreign(TEITag):
    targets = ['foreign']

    def get_replacement(self):
        langcode = self.get('{%s}lang' % config['xml_namespace'])
        language = config['languages'].get(langcode)
        if language:
            return '\\text%s{%s}' % (language, self.text)
        return self.text


class FloatingText(TEITag):
    targets = ['floatingText']

    def get_replacement(self):
        floattype = self.get('type')
        if floattype == 'verse':
            return self._verse()
        elif floattype == 'addition':
            return self._addition()
        self.raise_()

    def _verse(self):
        return '\n\\vspace{5mm}%s\\vspace{5mm}\n' % self.text

    def _addition(self):
        return '\\pstart %s\\pend' % self.text


# class SimpleTag(TEITag):
#     """Tag to be replaced using very simple rules"""
#     targets = ['label', 'add', 'space', 'deletion']

#     def get_replacement(self):
#         pass

class Label(TEITag):
    targets = ['label']

    def get_replacement(self):
        return '\\label{%s}' % self.attrib['n']


class Space(TEITag):
    targets = ['space']

    def get_replacement(self):
        maps = {'vertical': '\\bigskip',
             'horizontal': '\\hfill{}'}
        space = maps.get(self.get('n'))
        return space if space else '\\qquad{}'


class Deletion(TEITag):
    targets = ['del']

    def get_replacement(self):
        if self.get('resp'):
            return self.delete()
        elif self.get('hand'):
            return '\\sout{%s}' % self.text
        self.raise_()


class Add(TEITag):
    targets = ['add']

    def get_replacement(self):
        return '\\addition{%s}' % self.text

class Ptr(TEITag):
    
    targets = ['ptr']

    def get_replacement(self):
        _type = self.attrib['type']
        if _type == 'bibliog':
            return self._bibliog()
        elif _type == 'crossref':
            return self._crossref()
        self.raise_()

    def _target(self):
        return self.attrib['target'][1:]

    def _bibliog(self):
        pre = self.get('pre') or ''
        n = self.get('n') or ''
        square = lambda t: '[%s]' % t
        if pre:
            pre = square(pre)
        if pre or n:
            n = square(n)
        return ' \\autocite%s%s{%s}' % (pre, n, self._target())

    def _crossref(self):
        return '\\pageref{%s}' % self._target()


class Div(TEITag):
    targets = ['div']

    def get_replacement(self):
        divtype = self.get('type')
        if divtype in ['month', 'year']:
            self._process_date(divtype)
        return self.unwrap()

    def _process_date(self, divtype):
        if divtype == 'month':
            add = self.process_month()
        elif divtype == 'year':
            add = self.process_year()
        self.add_to_previous(add)

    def process_month(self):
        for parent in self.iterancestors('{*}div'):
            if parent.get('type') == 'year':
                year = parent.attrib['n']
                break
        return '\n\\addcontentsline{toc}{chapter}\
                {%s %s}' % (self.attrib['n'], year)

    def process_year(self):
        n = self.attrib['n']
        new_end = ''# '\\addtoendnotes{\\bigskip{}\\textbf{%s}\\bigskip{}}' % n
        new_contents = '\\addcontentsline{toc}{part}{%s}' % n
        return '\n%s %s' % (new_contents, new_end)

class Fmt():

    def __new__(cls, rend, name):

        fmt_names = config['fmt_names']
        monopoly = lambda key: frozenset(fmt_names[key])

        fmt_keys = ['emph', 'single', 'double', 'superscript', 'smcp']
        fmts = [monopoly(key) for key in fmt_keys]

        fmt_fmts = [('\\emph{', '}'), ("`", "'"), ("``", "''"),
                    ('\\textsuperscript{', '}'), ('\\textsc{', '}')]
                    
        fmt_funcs = {n: cls._wrap(*f) for n, f in zip(fmts, fmt_fmts)}

        for group in fmts:
            if rend in group:
                return fmt_funcs[group]

        return cls.by_default(name, fmt_funcs[fmts[1]], fmt_funcs[fmts[0]])

    def __init__(self):
        pass

    @staticmethod
    def _wrap(before, after):
        return partial('{0}{2}{1}'.format, before, after)

    @classmethod
    def by_default(cls, name, single, emph):
        if name in ['soCalled', 'q']:
            return single
        elif name == 'supplied':
            return cls._wrap('«', '»')
        elif name == 'bibl':
            return cls._wrap('', '')
        elif name in ['hi']:
            return emph


class FmtTag(TEITag):
    """A tag dependent on common formatting rules."""

    targets = ['soCalled', 'supplied', 'bibl', 'hi', 'q']

    def get_replacement(self):
        fmt_func = Fmt(self.get('rend'), self.localname)
        if fmt_func:
            return fmt_func(self.text)
        self.raise_()


class GenericTag(TEITag):
    """"Tags to be handled in a generic way."""

    deletes = ['lb']
    no_actions = ['corr', 'sic', 'lem', 'rdg']
    text_replaces = ['body', 'time', 'list', 'item', 'name']
    unwraps = ['subst', 'trait']
    targets = deletes + no_actions + text_replaces + unwraps

    def get_replacement(self):
        name = self.localname
        if name in self.text_replaces:
            return self.text
        elif name in self.unwraps:
            return self.unwrap()
        elif name in self.deletes:
            return self.delete()

class FilterTag(TEITag):

    """Tag handled with its children"""

    targets = ['app', 'choice']

    def get_replacement(self):
        if self.localname == 'choice':
            return self._choice()
        else:
            return self._app()

    def _choice(self):
        kids = map(self.textfinder, ['{*}corr', '{*}sic'])
        return '\\correction{%s}{%s}' % tuple(kids)

    def _app(self):
        rdgs = self.iterchildren('{*}rdg')
        witmaker = lambda tag: '\\wit{%s}{%s}' % (tag.text, tag.attrib['wit'])
        witnesses = ' '.join([witmaker(x) for x in rdgs])
        lem = self.textfinder('{*}lem')
        return '\\variants{%s}{%s}' % (lem, witnesses)

    def textfinder(self, term):
        x = self.find(term)
        if x is None:
            self.raise_()
        return x.text


class PageBreak(TEITag):
    targets = ['pb']

    def _init(self):
        super()._init()
        if self.tail:
            self.tail = self.tail.lstrip()
        previous = self.getprevious()
        if previous is not None and previous.tail:
            previous.tail = previous.tail.rstrip()

    def get_replacement(self):
        page_number = self._pagenumber()
        if page_number == '1':
            return self.delete()
        elif self._in_text():
            return self._text(page_number)
        else:
            return self._float(page_number)
        
    def _pagenumber(self):
        return self.attrib['n'].lstrip('0')
        if pagenumber == '1':
            return self._no_show()
        return p

    def _in_text(self):
        return self.getparent().localname in ['p', 'lg']

    def _float(self, pagenumber):
        return '\n\\floatpagebreak{[%s]}\n' % pagenumber

    def _text(self, pagenumber):
        return ' \\intextpagebreak{[%s]} ' % pagenumber



class PersName(TEITag):
    targets = ['persName']

    def _init(self):
        super()._init()
        self.in_body = self._check_if_in_body()

    def get_replacement(self):
        ref = self.attrib['ref'][1:]
        
        if ref == '??':
            return self._unknown()
        return self._known(ref)

    def _unknown(self):
        return '\\unknownperson{%s}' % self.text

    def _known(self, ref):

        person = self.persdict[ref]

        def _index():
            t = (person.indexname + '|innote', self.text)
            return '\\indexperson{%s}{%s}' % t

        def _person():
            t = (ref, person.indexname, person.description, self.text)
            return '\\person{%s}{%s}{%s}{%s}' % t

        if person.indexonly or not self.in_body:
            return _index()
        return _person()

# END OF TAGS

class ParserMethods():
    """Methods for parsing and transforming XML."""

    def __init__(self):
        self._parser = None

    @staticmethod
    def transform_tree(tree, persdict, in_body=True):
        """Transform a tree."""
        for tag in sorted(list(tree.getiterator('*'))):
            if tag.localname == 'persName':
                tag.process(persdict, in_body=in_body)
            else:
                tag.process()
        return tree

    @property
    def parser(self):
        """Return a parser. A property not an attribute
           so that the parser can be constructed w/r/t
           a config that takes account of user settings.
        """
        if not self._parser:
            self._parser = self.make_parser()
        return self._parser

    def parse(self, textpath):
        """Parse textpath"""
        return etree.parse(textpath, self.parser)

    @classmethod
    def make_parser(cls):
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

parser = ParserMethods()
