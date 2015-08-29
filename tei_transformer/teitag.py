import re
import calendar
from lxml import etree

from .importer import config

class TEITag(etree.ElementBase):
    
    """ Base class for TEI tags, to be used while parsing."""

    def _init(self):
        self._localname = None
        if self.text:
            self.text = self.texify(self.text)
        if self.tail:
            self.tail = self.texify(self.tail)

    @staticmethod
    def texify(text):
        """Convert unicode to latex commands. Very slow, but probably better this way than on the text as a whole."""
        for key, value in config.unicode_to_latex().items():
            text = text.replace(key, value)
        return text

    def __str__(self):
        return etree.tounicode(self, with_tail=False)


    @property
    def localname(self):
        
        """Return the localname of a tag: the tag name without namespacing.
        Equivalent to etree.QName(self).localname"""

        if not self._localname:
            self._localname = etree.QName(self).localname
        return self._localname
    
    @property
    def replacement(self):

        """Wrapper around the method to return a replacement for the tag."""

        return self.get_replacement()
    
    @property
    def number_of_descendants(self):

        """Return the number of descendants the tag has"""

        if len(self) == 0:
            return 0
        else:
            return sum(1 for _ in self.iterdescendants())
    
    def delete(self):

        """Remove a tag from the tree, preserving its tail"""

        if self.tail:
            parent = self._previoustail_or_parenttext(self.tail)
        else:
            parent = self.getparent()
        parent.remove(self)

    def get_replacement(self):

        """Abstract method replaced by base classes"""

        raise NotImplementedError('You need to write a class to replace tags of type `%s\'' % self.localname)

    def unwrap(self):

        """Replace a tag with its children"""

        children = list(self.iterchildren(reversed=True))

        if not len(children):
            compleat_text = self._resilientext(self.text, self.tail)
            parent = self._previoustail_or_parenttext(compleat_text)
            parent.remove(self)
        else:
            parent = self.getparent()
            index = parent.index(self)
            last_child = children[-1]
            last_child.tail = self._resilientext(last_child.tail, self.tail)
            parent = self._previoustail_or_parenttext(compleat_text)
            for child in children:
                parent.insert(index, child)

    def _previoustail_or_parenttext(self, addtext):
        previous = self.getprevious()
        parent = self.getparent()
        if previous is not None:
            previous.tail = self._resilientext(previous.tail, addtext)
        else:
            parent.text = self._resilientext(parent.text, addtext)
        return parent

    def replace_with(self, replacement):

        """Replace a tag with a string"""

        replacement = replacement + (self.tail or '')
        parent = self._previoustail_or_parenttext(replacement)
        parent.remove(self)

    @staticmethod
    def _resilientext(arg1, arg2):
        return (arg1 or '') + (arg2 or '')

    def insert_string_before(self, insertion):

        """Insert a string immediately before a tag"""

        self._previoustail_or_parenttext(insertion)


class Body(TEITag):

    target = 'body'
    
    def get_replacement(self):
    
        """ Return the replacement for a tag of type <body>"""

        return self.text

class Hi(TEITag):

    target = 'hi'
    
    def get_replacement(self):
    
        """ Return the replacement for a tag of type <hi>"""

        rend = self.get('rend')
        if rend == 'super':  # Superscript.
            return '\\textsuperscript{%s}' % self.text
        elif rend == 'sub':  # Subscript
            return '\\textsubscript{%s}' % self.text
        elif rend == 'italic' or rend == 'underline':
            return '\\emph{%s}' % self.text
        elif rend == 'smcp':  # Small caps
            return '\\textsc{%s}' % self.text
        else:
            return '\\emph{%s}' % self.text

class Name(TEITag):

    target = 'name'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <name>"""

        if self.get('type') == 'ship' and self.get('rend') == 'italic':
            return '\\emph{%s}' % self.text
        return self.text

class Ptr(TEITag):

    target = 'ptr'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <ptr>"""

        target = self.get('target')[1:]
        kind = self.get('type')
        if kind == 'bibliog':
            if self.get('n'):
                return ' \\autocite[%s]{%s}' % (self.get('n'), target)
            return ' \\autocite{%s}' % target
        elif kind == 'crossref':
            return '\\pageref{%s}' % target  

class Deletion(TEITag):

    target = 'del'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <del>"""

        if self.get('resp'):
            return self.delete()
        elif self.get('hand'):
            return '\\sout{%s}' % self.text

class Supplied(TEITag):

    target = 'supplied'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <supplied>"""

        """process <supplied>"""
        return '«%s» ' % self.text

class Add(TEITag):

    target = 'add'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <add>"""

        if self.text and not len(self.text) == 1:
            contents = self.text.strip('([])/')
            startswithcommand = re.match(r'\\\w+[{]', contents)
            if not startswithcommand:
                contents = contents.strip('\\')
            else:
                contents = contents.rstrip('\\')
            if contents.endswith('.'):
                if contents[-2] in ')]':
                    contents = contents[:-2] + '.'
        else:
            contents = self.text
        
        if self.get('resp'):
            return '\\lbrack %s\\rbrack{}' % contents
        elif self.get('hand'):
            return '\\lbrack %s\\rbrack{}' % contents

class Quote(TEITag):

    target = 'q'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <q>"""

        rendering = self.get('rend')
        if rendering == 'single':
            return "`%s'" % self.text
        elif rendering == 'double':
            return "``%s''" % self.text
        # Let's stick with OUP style for this project.
        return "`%s'" % self.text

        return replacement

class SoCalled(TEITag):

    target = 'soCalled'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <soCalled>"""

        return "`%s'" % self.text

class Bibl(TEITag):

    target = 'bibl'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <bibl>"""

        rendering = self.get('rend')

        singlequotes = ['single']
        doublequotes = ['double']
        italics = ['italic']

        if rendering in singlequotes:
            return "`%s'" % self.text
        elif rendering in doublequotes:
            return "``%s''" % self.text
        elif rendering in italics:
            return '\\emph{%s}' % self.text
        elif rendering == 'none' or not rendering:
            return self.text
        else:
            print('I didn\'t know how to render %s.' % rendering)
            return self.text

class Choice(TEITag):

    target = 'choice'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <choice>"""

        for x in self.getchildren():
            if x.localname == 'sic':
                sic = x
            elif x.localname == 'corr':
                corr = x
        return '\\edtext{%s}{\\Afootnote{%s}}' % (corr.text, sic.text)

class Corr(TEITag):

    target = 'corr'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <corr>"""

        return None

class Sic(TEITag):

    target = 'sic'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <sic>"""

        return None

class Time(TEITag):

    target = 'time'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <time>"""

        """process <time>"""
        return self.text

class Space(TEITag):

    target = 'space'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <space>"""

        spacetype = self.get('n')

        if spacetype == 'vertical':
            return '\\bigskip'
        elif spacetype == 'horizontal':
            return '\\hfill{}'
        else:
            return '\\qquad{}'
        print('Spaces of type %s are not defined.' % spacetype)

class Foreign(TEITag):

    target = 'foreign'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <foreign>"""

        langcode = self.get('%slang' % '{http://www.w3.org/XML/1998/namespace}')

        languagedict = config.languages_used()
        language = languagedict.get(langcode)


        if language:
            return '\\text%s{%s}'\
                % (language, self.text)
        print('Language %s not defined.' % langcode)
        return self.text

class Paragraph(TEITag):

    target = 'p'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <p>"""

        if not self.text:
            return self.delete()

        paratext = self.text.strip()
        paratext = paratext.replace('\n', ' ')

        rendering = self.get('rend')

        if rendering == 'noindent':
            indent = '\\noindent '
        elif rendering == 'indent ':
            indent = '\\indent '
        elif rendering == 'doubleindent':
            indent = '\\indent \\qquad{} '
        else:
            # Our headers are wrapped in an eledmac paragraph.
            # So latex doesn't know not to indent them.
            previous = self.getprevious()
            if previous is not None and previous.localname == 'head':
                indent = '\\noindent '
            else:
                indent = ' '

        replacement = indent + paratext

        replacement = '\n\\pstart %s\\pend' % replacement
        replacement = replacement.replace(' & ', ' \\&amp; ')
        return replacement

class FloatingText(TEITag):

    target = 'floatingText'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <floatingText>"""

        floattype = self.get('type')
        if floattype == 'verse':
            return self.text
        elif floattype == 'addition':
            return self.process_floating_addition()

    def process_floating_addition(self):
        return '\\pstart %s\\pend'\
                % self.text

class VerseLine(TEITag):

    target = 'l'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <l>"""

        if self.tail:
            self.tail = self.tail.strip()
        return self.text.strip() + ' &\n'

class VerseLineGroup(TEITag):

    target = 'lg'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <lg>"""

        if self.tail:
            self.tail = self.tail.strip()
        stanzatext = self.text.strip()
        stanzatext = stanzatext.rstrip('&')
        return '\n\n\\stanza\n%s \\&\n\n' % stanzatext

class Head(TEITag):

    target = 'head'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <head>"""

        # Make explicit the desire not to indent following paragraph.
        if not self.tail or not self.tail.strip():
            next_sibling = self.getnext()
            if next_sibling is not None and next_sibling.localname == 'p':
                if next_sibling.get('rend') == None:
                    next_sibling.text = '\\noindent %s' % (next_sibling.text or '')

        parent_attrs = self.getparent().attrib
        div_type = parent_attrs.get('type')
        identifier = parent_attrs.get('%sid' % '{http://www.w3.org/XML/1998/namespace}')
        # if div_type == None: # Part
        #     return self.process_head_level_one(contents)
        if div_type == 'title': # Chapter
            return self.process_head_level_two()
        elif div_type == 'diaryentry': # Section
            return self.process_head_level_three(identifier)
        elif div_type == 'diaryentrysection': # Subsection
            return self.process_head_level_four(identifier)

    def process_head_level_one(self):
        return '\\part{%s}' % self.text

    def process_head_level_two(self):
        return '\\pstart\n\\eledchapter*{%s}\n\\pend' % self.text

    def process_head_level_three(self, identifier):
        assert identifier is not None
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

class PersName(TEITag):

    target = 'persName'

    def _init(self):
        self._localname = None

        self.no_persdict = False
        self.is_body_text = True
        self.persname_used = False
        self.indexphrase = None
        self.replacephrase = None
        self.indexing_only = False

    def preprocess(self, persdict):

        """Collect information related to the persdict, so outside the parse tree"""


        ref = self.get('ref')
        if ref:
            ref = ref[1:]
        if ref and not ref == '??':
            person = persdict.get(ref)
            if person:
                self.identified = True
            else:
                self.identified = False
                print('\nCould not identify %s: %s \n' % (self.get('ref'), self.text))
        else:
            self.identified = False

        self.is_body_text = self.check_if_body_text()

        if self.identified:
            if self.is_body_text:
                self.indexphrase = '\\index{%s}' % (person.get('indexname'))
            else:
                self.indexphrase = '\\index{%s|innote}' % (person.get('indexname'))
            self.indexing_only = person.get('indexing_only')
            self.replacephrase = person.get('replacephrase')
            self.persname_used = person.get('persname_used')
            if not self.persname_used and self.is_body_text:
                persdict[ref]['persname_used'] = True

    
    def get_replacement(self):
    
        """ Return the replacement for a tag of type <persName>"""

        if self.no_persdict:
            return self.text

        if self.identified:
            if self.indexing_only:
                return self.text + self.indexphrase
            if not self.persname_used:
                if self.is_body_text:
                    return '\\edtext{%s}{\\Bfootnote{%s}}%s'\
                        % (self.text, self.replacephrase, self.indexphrase)
            return self.text + self.indexphrase

        if self.is_body_text:
            return '\\edtext{%s}{\\Bfootnote{Not identified}}'\
                    % self.text

        return self.text

    def check_if_body_text(self):

        """Check that the tag is not within a note.
        Will not override the attribute self.is_body_text if this is False"""

        if not self.is_body_text:
            return False
        for x in self.iterancestors('{*}note'):
            return False
        return True

class PageBreak(TEITag):

    target = 'pb'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <pb>"""

        pagenumber = self.get('n')
        pagenumber = pagenumber.lstrip('0')
        if pagenumber == '1':
            return self.delete()

        if self.tail is not None:
            self.tail = self.tail.lstrip()
        previous = self.getprevious()
        if previous is not None:
            if previous.tail:
               previous.tail = previous.tail.rstrip()

        parent = self.getparent()
        if parent.localname in ['p', 'lg'] :
            return ' \\textbar{} \\ledsidenote{[%s]}' % pagenumber
        else:
            return '\n\pstart \\ledsidenote{[%s]}  \pend\n' % pagenumber

class TextualVariant(TEITag):

    target = 'app'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <app>"""

        return '\\edtext{%s' % self.text

class Lemma(TEITag):

    target = 'lem'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <lem>"""

        return '\\edtext{%s}' % self.text

class VariantReading(TEITag):

    target = 'rdg'

    def get_replacement(self):
        
        """ Return the replacement for a tag of type <rdg>"""

        witness = self.get('wit')
        replacement = '%s \\textbf{%s}' % (self.text, witness)

        if self.previous_sibling_name != 'wit':
            replacement = '{\\Afootnote{' + replacement

        if self.next_sibling_name != 'wit':
            replacement += '}}'

        return replacement

class TextualNote(TEITag):

    target = 'note'

    def _init(self):
        self._localname = None
        self.defstring = None

    def has_contents(self):

        """Return whether this note is not empty"""

        return self.text is not None or len(self.getchildren()) is not 0

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <note>"""

        if not self.has_contents(): # i.e. is a marker
            return None

        marker, inbetweens = self.get_marker()
        bodytext = self.get_bodytext(marker, inbetweens)

        note_type = self.get('type')
        if note_type == 'gloss':
            return self.process_gloss(marker, bodytext)
        elif note_type == 'annotation':
            return self.process_annotation(marker, bodytext)

    def get_marker(self):

        """Find the tag which marks the beginning of the text to
        which this note refers"""

        marker = None
        inbetweens = False
        skipone = False
        for prev_sib in self.itersiblings(preceding=True):
            if prev_sib.localname == 'note':
                if prev_sib.text:
                    skipone = True
                else:
                    if not skipone:
                        marker = prev_sib
                        break
                    else:
                        skipone = False
            else:
                inbetweens = True
        try:
            assert marker is not None
        except:
            print('\nCould not find marker for %s' % self.text)
            exit()
        return marker, inbetweens

    def get_bodytext(self, marker, inbetweens):

        """ Return the text content between note and marker.
        Tags of type <rdg> and <sic> are excluded."""

        if not inbetweens:
            self.bodytext_is_tail = True
            return marker.tail
        else:
            self.bodytext_is_tail = False
            inbetweens = []
            if marker.tail:
                inbetweens.append(marker.tail)
            for x in marker.itersiblings():
                if x == self:
                    break
                elif x.localname in ['rdg', 'sic']:
                    pass
                else:
                    descendants = list(x.iterdescendants())
                    for y in reversed(descendants):
                        if y.localname in ['rdg', 'sic']:
                            pass
                        else:
                            if y.text:
                                inbetweens.append(y.text)
                            if y.tail:
                                inbetweens.append(y.tail)
            return ''.join(inbetweens) 

    def process_annotation(self, marker, bodytext):

        """Process notes where type=\"annotation\""""

        short_lemma = self.get_short_lemma(bodytext)
        marker.replace_with('\\edtext{')
        if short_lemma:
            return '}{\lemma{%s}\\Bfootnote{%s}}' % (short_lemma, self.text)
        else:
            return '}{\\Bfootnote{%s}}' % self.text

    def process_gloss(self, marker, bodytext):

        """Process notes where type=\"gloss\""""

        if bodytext.find('&') == -1:
            self.defstring = '\n'.join(['\\newglossaryentry{%s}' % bodytext,
                                        '{name = {%s},' % bodytext,
                                        'description = {%s}' % self.text,
                                        '}'])
        else:  # Glossaries package doesn't handle ampersands well.
            bodystring = re.sub(r'(?<!\\)&', '\\&', bodytext)
            glossname = bodytext.replace('&', '')
            if self.bodytext_is_tail:
                marker.tail = glossname
            else:
                bodytext.replace_with(glossname)
            self.defstring = '\n'.join(['\\newglossaryentry{%s}' % glossname,
                                        '{name = {%s},' % bodystring,
                                        'description = {%s}' % self.text,
                                        '}'])
        marker.replace_with('\\gls{')
        return '}'

    def get_short_lemma(self, lemma):

        """Return a shortened lemma to be used to label the note"""

        short_lemma = None

        if len(lemma) > 50:
            while lemma.find('edtext') != -1: # Can be stacked edtexts.
                lemma = re.sub(r'(?s)\\edtext\{(.*?)\}\{(.*?)\}\}', r'\1', lemma)
            lemma = re.sub(r'\\index\{.*?\}', '', lemma)
            lemma = re.sub(r'\\edindex\{.*?\}', '', lemma)
        if len(lemma) > 50:
            split_lemma = lemma.strip().split()
            if len(split_lemma) > 5:
                short_lemma = ' '.join([split_lemma[0],
                                        split_lemma[1],
                                        '\\dots\\',
                                        split_lemma[-2],
                                        split_lemma[-1]
                                        ])
            elif len(split_lemma) > 3:
                short_lemma = ' '.join([split_lemma[0],
                                        '\\dots\\',
                                        split_lemma[-1]
                                        ])

        if short_lemma is not None:
            if short_lemma.find('}') == -1:
                return short_lemma
            else:
                left_curls = short_lemma.count('{')
                right_curls = short_lemma.count('}')
                if left_curls == right_curls:
                    return short_lemma
                else:
                    if left_curls >= 1 and right_curls == 0:
                        return short_lemma.replace('{', '')
                    elif right_curls >= 1 and left_curls == 0:
                        return short_lemma.replace('}', '')
                    else:
                        print(short_lemma)
                        print('Mismatched brackets.')
                        exit()

class LineBreak(TEITag):

    target = 'lb'
    
    def get_replacement(self):
    
        """ Return the replacement for a tag of type <lb>"""

        return self.delete()


class Subst(TEITag):

    target = 'subst'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <subst>"""

        return self.unwrap()

class List(TEITag):

    target = 'list'
    
    def get_replacement(self):
    
        """ Return the replacement for a tag of type <list>"""

        return self.text

class ListItem(TEITag):

    target = 'item'
    
    def get_replacement(self):
    
        """ Return the replacement for a tag of type <item>"""

        return self.text

class Div(TEITag):

    target = 'div'

    def get_replacement(self):
    
        """ Return the replacement for a tag of type <div>"""

        divtype = self.get('type')
        date = self.get('n')
        if divtype == 'year':
            before = self.process_year(date)
        elif divtype == 'month':
            year = False
            for parent in self.iterancestors('{*}div'):
                if parent.get('type') == 'year':
                    parentyear = parent.get('n')
                    break
            before = self.process_month(date, parentyear)
        else:
            return self.unwrap()

        self.insert_string_before(before)
        return self.unwrap()

    def process_year(self, date):
        """process year"""
        return '\n\\addcontentsline{toc}{part}{%s}' % date

    def process_month(self, month, year):
        """process month"""
        return '\n\\addcontentsline{toc}{chapter}\
                      {%s %s}\n\\rfoot{\\textsc{%s} %s / \\thepage}'\
                      % (month, year, month, year)
