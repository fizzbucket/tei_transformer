from lxml import etree
from .tags import TEITag
import sys

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
        return self._parse(str(textpath))

    def _parse(self, textpath):
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