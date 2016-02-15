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
        if replacement is None:  # So we need the more specific test.
            return  # i.e. don't touch this.
        else:
            self.replace_w_str(replacement)

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
        if any(True for _ in note_ancestors):
            return False
        return True



class Head(TEITag):

    targets = ['head']

    def get_replacement(self):
        """ Return the replacement for a tag of type <head>"""

        # Make explicit the desire not to indent following paragraph.
        if not self.tail or not self.tail.strip():
            next_sibling = self.getnext()
            if next_sibling is not None and next_sibling.localname == 'p':
                if next_sibling.get('rend') is None:
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
        if identifier is None:
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
        marker.replace_w_str('\\annotationlem{')
        abbreviation = self._process_text_contents(abbreviation)
        return '}{%s}{%s}' % (abbreviation, self.text)

    def unabbreviated_lemma(self, marker):
        marker.replace_w_str('\\annotation{')
        return '}{%s}' % self.text

    def empty(self):
        return self.text is None and len(self.getchildren()) == 0

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

    def get_replacement(self):

        in_bio = self.getparent().localname == 'trait'

        if in_bio:
            if not self.text:
                return ''
        try:
            self.text = self.text.strip()
        except AttributeError:
            self.raise_()

        paratext = self.text.replace('\n', ' ')

        if in_bio or not self._check_if_in_body():
            if self.getnext() is not None or self.tail:
                return '%s\\par ' % paratext
            else:
                return paratext

        rend = self.get('rend')
        if rend == 'noindent':
            indent = '\\noindent'
        elif rend == 'indent':
            indent = '\\indent'
        elif rend == 'doubleindent':
            indent = '\\doubleindent'
        else:
            # Our headers are wrapped in an eledmac paragraph.
            # So latex doesn't know not to indent them.
            indent = self._after_head_indent()

        return ' '.join(['\n\\pstart', indent, paratext, '\\pend'])

    def _after_head_indent(self):
        previous = self.getprevious()
        if previous is not None and previous.localname == 'head':
            # There was a tag there, but it's been processed already.
            if previous.tail and previous.tail.strip():
                return ''
            # We're the first thing following.
            else:
                return '\\noindent'
        # Not a head. Default to no indent.
        return ''


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
        return '\n\\addcontentsline{toc}{part}{%s}' % self.attrib['n']

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
