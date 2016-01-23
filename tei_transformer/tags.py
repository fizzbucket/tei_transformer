from lxml import etree
import calendar

LANGUAGES = {
    'it': 'italian',
    'de': 'german',
    'la': 'latin',
    'fr': 'french',
    'gr': 'greek',
}

XML_NAMESPACE = '{http://www.w3.org/XML/1998/namespace}'


class ImplementationError(Exception):
    pass

class FmtMethods():

    def _wrap(self, before, after, text=None):
        if text is None:
            text = self.text
        return '%s%s%s' % (before, text, after)

    def square_brackets(self, text=None):
        return self._wrap('[', ']', text)

    def single_quotes(self, text=None):
        return self._wrap('`', "'", text)

    def double_quotes(self, text=None):
        return self._wrap("``", "''", text)

    def emph(self, text=None):
        if text is None:
            text = self.text
        return '\\emph{%s}' % text

    def superscript(self, text=None):
        if text is None:
            text = self.text
        return '\\textsuperscript{%s}' % text

    def smallcaps(self, text=None):
        if text is None:
            text = self.text
        return '\\textsc{%s}' % text

    def handle_none(self):
        return self.text

    def _singles(self):
        return ['single']

    def _doubles(self):
        return ['double']

    def _emphs(self):
        return ['emph', 'italic', 'underscore', 'underline']

    def _supers(self):
        return ['super', 'upper']

    def _smcps(self):
        return ['smcp']

    def _none(self):
        return [None, 'none', 'None']

    def fmt_lists(self):
        return [(self._emphs(), self.emph),
                (self._singles(), self.single_quotes),
                (self._doubles(), self.double_quotes),
                (self._supers(), self.superscript),
                (self._smcps(), self.smallcaps),
                (self._none(), self.handle_none)]

class TEITag(etree.ElementBase):

    def _init(self):
        self._localname = None
        if self.text:
            self.text = self._process_text_contents(self.text)
        if self.tail:
            self.tail = self._process_text_contents(self.tail)
        self._descendants_count = None

    # RICH COMPARISONS TO ALLOW SORTING
    @property
    def descendants_count(self):
        if not self._descendants_count:
            if self.no_children():
                self._descendants_count = 0
            else:
                self._descendants_count = sum(1 for _ in self.iterdescendants())
        return self._descendants_count
    
    def __eq__(self, other):
        return self.descendants_count == other.descendants_count

    def __lt__(self, other):
        return self.descendants_count < other.descendants_count

    def process(self, persdict=None, in_body=True):

        # Check to see we won't accidentally wipe something out.
        not_good_children = self.localname not in ['choice', 'app']
        if not self.no_children() and not_good_children:
            self.raise_()
        # Now on with the replacement.
        if self.localname == 'persName':
            replacement = self.get_replacement(persdict, in_body)
        else:
            replacement = self.get_replacement()
        if not replacement:
            return  # i.e. don't touch this.
        else:
            self.replace_w_str(replacement)

    @property
    def localname(self):
        """Tag name without namespace"""
        if not self._localname:
            self._localname = etree.QName(self).localname
        return self._localname

    def no_children(self):
        """Return true if self has no children"""
        return len(self) == 0

    def _process_text_contents(self, text):
        """Function called to manipulate text in tags or tail when first parsed.
        Currently takes no action; might be used,
        for example, to replace unicode with latex symbols"""
        return text

    def __str__(self):
        return etree.tounicode(self, with_tail=False)

    def delete(self):
        """Remove this tag from the tree, preserving its tail"""
        parent = self.add_to_previous(self.tail)
        parent.remove(self)

    def get_replacement(self):
        """Called to get a string replacement for a tag"""
        raise NotImplementedError(self)

    def unwrap(self):
        """Replace tag with contents, including children"""
        children = list(self.iterchildren(reversed=True))
        if not len(children):
            self.replace_w_str(self.text)
        else:
            parent = self.getparent()
            index = parent.index(self)
            last_child = children[-1]
            last_child.tail = self.textjoin(last_child.tail, self.tail)
            parent = self.add_to_previous(self.textjoin(self.text, self.tail))
            for child in children:
                parent.insert(index, child)

    def replace_w_str(self, replacement):
        """Replace tag with string"""
        replacement = self.textjoin(replacement, self.tail)
        parent = self.add_to_previous(replacement)
        parent.remove(self)

    def add_to_previous(self, addition):
        """Add text to the previous tag"""
        previous = self.getprevious()
        parent = self.getparent()
        if previous is not None:
            previous.tail = self.textjoin(previous.tail, addition)
        else:
            parent.text = self.textjoin(parent.text, addition)
        return parent

    @staticmethod
    def textjoin(a, b):
        """Join a and b, replacing either with an empty string
        if their value is not True"""
        return ''.join([(a or ''), (b or '')])

    def raise_(self):
        """Raise an implemenation error with self as argument"""
        raise ImplementationError(self)

    def required_key(self, key):
        x = self.get(key)
        if x:
            return x
        self.raise_()


# STANDARD

class Head(TEITag):

    target = 'head'

    def get_replacement(self):

        """ Return the replacement for a tag of type <head>"""

        # Make explicit the desire not to indent following paragraph.
        if not self.tail or not self.tail.strip():
            next_sibling = self.getnext()
            if next_sibling is not None and next_sibling.localname == 'p':
                if next_sibling.get('rend') is None:
                    next_sibling.text = '\\noindent %s' % (next_sibling.text or '')

        parent_attrs = self.getparent().attrib
        div_type = parent_attrs['type']
        if div_type == 'title':  # Chapter
            return self.process_head_level_two()

        try:
            identifier = parent_attrs['%sid' % '{http://www.w3.org/XML/1998/namespace}']
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

    target = 'note'

    def get_replacement(self):
        if self.empty():
            return

        marker = self.get_marker()
        if marker is False or self.get('type') != 'annotation':
            self.raise_()
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
    target = 'p'


    def get_replacement(self):
        try:
            self.text = self.text.strip()
        except AttributeError:
            self.raise_()

        paratext = self.text.replace('\n', ' ')
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
    target = 'lg'

    def _init(self):
        super()._init()
        if self.tail:
            self.tail = self.tail.strip()

    def get_replacement(self):
        stanzatext = self.text.strip()
        stanzatext = stanzatext.rstrip('&')
        return '\n\n\\stanza\n%s \\&\n\n' % stanzatext


class VerseLine(TEITag):
    target = 'l'

    def _init(self):
        super()._init()
        if self.tail:
            self.tail = self.tail.strip()
        if self.text:
            self.text = self.text.strip()

    def get_replacement(self):
        return '%s &\n' % self.text


class Foreign(TEITag):
    target = 'foreign'

    def get_replacement(self):
        langcode = self.get('%slang' % XML_NAMESPACE)
        language = LANGUAGES.get(langcode)
        if language:
            return '\\text%s{%s}' % (language, self.text)
        return self.text


class FloatingText(TEITag):
    target = 'floatingText'

    def get_replacement(self):
        floattype = self.get('type')
        if floattype == 'verse':
            return '\n\\vspace{5mm}%s\\vspace{5mm}\n' % self.text
        elif floattype == 'addition':
            return '\\pstart %s\\pend' % self.text
        self.raise_()

class ExternalReferenceTag(TEITag):
    
    def ex_ref(self, key):
        key = self.required_key(key)
        return key[1:]

    def key_or_empty(self, key):
        return self.get(key) or ''


class Ptr(ExternalReferenceTag, FmtMethods):

    target = 'ptr'

    def get_replacement(self):
        target = self.ex_ref('target')
        kind = self.get('type')

        bib = kind == 'bibliog'
        crossref = kind == 'crossref'

        if bib:
            pre = self.key_or_empty('pre')
            if pre:
                pre = self.square_brackets(pre)
            n = self.key_or_empty('n')
            if pre or n:
                n = self.square_brackets(n)
            return ' \\autocite%s%s{%s}' % (pre, n, target)
        elif crossref:
            return '\\pageref{%s}' % target

        self.raise_()


class PersName(ExternalReferenceTag):
    target = 'persName'

    def _init(self):
        super()._init()
        self.in_body_text = True
        note_ancestors = self.iterancestors('{*}note')
        if any(True for _ in note_ancestors):
            self.in_body_text = False

    def get_replacement(self, persdict, in_body):
        ref = self.ex_ref('ref')
        if ref == '??':
            return '\\unknownperson{%s}' % self.text

        if not in_body:
            self.in_body_text = False

        person = persdict[ref]
        indexonly = person.get('indexing_only')
        indexname = person['indexname']
        if indexonly or not self.in_body_text:
            if not self.in_body_text:
                indexname += '|innote'
            return '\\indexperson{%s}{%s}' % (indexname, self.text)
        else:
            description = person.get('description')
            return '\\person{%s}{%s}{%s}{%s}' % (ref, indexname, description, self.text)


class Label(TEITag):
    target = 'label'

    def get_replacement(self):
        n = self.required_key('n')
        return '\\label{%s}' % n



class Space(TEITag):
    target = 'space'

    def get_replacement(self):
        n = self.get('n')
        if n == 'vertical':
            return '\\bigskip'
        elif n == 'horizontal':
            return '\\hfill{}'
        else:
            return '\\qquad{}'
        self.raise_()

class Div(TEITag):
    target = 'div'

    def get_replacement(self):
        divtype = self.get('type')
        if not divtype:
            return self.unwrap()
        elif divtype in ['month', 'year']:
            date = self.required_key('n')
            if divtype == 'month':
                year = self._find_year()
                assert year
                before = '\n\\addcontentsline{toc}{chapter}\
                      {%s %s}' % (date, year)
            elif divtype == 'year':
                before = '\n\\addcontentsline{toc}{part}{%s}' % date

            self.add_to_previous(before)
        return self.unwrap()

    def _find_year(self):
        for parent in self.iterancestors('{*}div'):
            if parent.get('type') == 'year':
                return parent.required_key('n')




class PageBreak(TEITag):
    target = 'pb'

    def _init(self):
        super()._init()
        has_tail = self.tail is not None
        previous = self.getprevious()
        has_previous = previous is not None

        if has_tail:
            self.tail = self.tail.lstrip()
        if has_previous:
            if previous.tail:
                previous.tail = previous.tail.rstrip()

    def get_replacement(self):

        pagenumber = self.required_key('n')
        pagenumber = pagenumber.lstrip('0')
        if pagenumber == '1':
            return self.delete()

        parent = self.getparent()
        try:
            in_text = parent.localname in ['p', 'lg']
        except AttributeError:
            self.raise_()

        if in_text:
            return ' \\intextpagebreak{[%s]} ' % pagenumber
        else:
            return '\n\\floatpagebreak{[%s]}\n' % pagenumber


class Deletion(TEITag):
    target = 'del'

    def get_replacement(self):
        if self.get('resp'):
            return self.delete()
        elif self.get('hand'):
            return '\\sout{%s}' % self.text
        else:
            self.raise_()


class Add(TEITag):
    target = 'add'

    def get_replacement(self):
        return '\\addition{%s}' % self.text


class FilterTag(TEITag):

    def filterchildren(self, targets):
        searchtargets = map(lambda s: '{*}%s' % s, targets)
        for x in self.iterchildren(searchtargets):
            yield x.localname, x
            targets.remove(x.localname)

        if len(targets) != 0:
            self.raise_()


class Choice(FilterTag):
    target = 'choice'

    def get_replacement(self):
        for name, tag in self.filterchildren(['sic', 'corr']):
            if name == 'sic':
                sic_text = tag.text
            elif name == 'corr':
                corr_text = tag.text

        return '\\correction{%s}{%s}' % (corr_text, sic_text)


class TextualVariant(FilterTag):
    target = 'app'

    def get_replacement(self):
        rdgs = []
        for name, tag in self.filterchildren(['lem', 'rdg']):
            if name == 'lem':
                lem_text = tag.text
            elif name == 'rdg':
                rdgs.append(tag)

        rdgs = map(self.rdgs_map, rdgs)
        return '\\variants{%s}{%s}' % (lem_text, ' '.join(rdgs))

    @staticmethod
    def rdgs_map(rdg):
        try:
            wit = rdg.attrib['wit']
        except KeyError:
            rdg.raise_()
        return '\\wit{%s}{%s}' % (rdg.text, wit)

# FURTHER SUBCLASSING.



class SoCalled(TEITag, FmtMethods):
    target = 'soCalled'

    def get_replacement(self):
        return self.single_quotes()


class Supplied(TEITag, FmtMethods):
    target = 'supplied'

    def get_replacement(self):
        return self._wrap('«', '»')


class RendTag(TEITag, FmtMethods):

    def _rendery(self, required=False):
        if not required:
            rend = self.get('rend')
        else:
            rend = self.required_key('rend')
        for targets, func in self.fmt_lists():
            if rend in targets:
                return func()
        self.raise_()


class Bibl(RendTag):
    target = 'bibl'

    def get_replacement(self):
        return self._rendery()


class Hi(RendTag):
    target = 'hi'

    def get_replacement(self):
        return self._rendery(required=True)


class Quote(RendTag):
    target = 'q'

    def handle_none(self):
        return self.single_quotes()

    def get_replacement(self):
        return self._rendery()

# SIMPLE ONES:


class DeleteMe(TEITag):

    """Delete tags of this type"""

    target = ['lb']

    def get_replacement(self):
        return self.delete()


class DontTouchMe(TEITag):

    """Take no action with tags of this type"""

    target = ['corr', 'sic', 'lem', 'rdg']

    def get_replacement(self):
        return None


class ReplaceMeWText(TEITag):

    """Replace tags of this type with their text"""

    target = ['body', 'time', 'list', 'item', 'name']

    def get_replacement(self):
        return self.text


class UnWrapMe(TEITag):

    """Unwrap tags of this type"""

    target = ['subst']

    def get_replacement(self):
        return self.unwrap()