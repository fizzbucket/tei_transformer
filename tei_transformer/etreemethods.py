from lxml import etree

class EtreeMethods():
    """A mixin class providing some useful methods for etree elements."""

    def __eq__(self, other):
        if not isinstance(other, EtreeMethods):
            return NotImplemented
        return self.descendants_count() == other.descendants_count()

    def __lt__(self, other):
        if not isinstance(other, EtreeMethods):
            return NotImplemented
        return self.descendants_count() < other.descendants_count()

    def __str__(self):
        return etree.tounicode(self, with_tail=False)

    def descendants_count(self):
        """Number of descendants"""
        if len(self) == 0:
            return 0
        return sum(1 for _ in self.iterdescendants())

    @property
    def localname(self):
        """Tag name without namespace"""
        return etree.QName(self).localname

    def delete(self):
        """Remove this tag from the tree, preserving its tail"""
        parent = self.add_to_previous(self.tail)
        parent.remove(self)

    def unwrap(self):
        """Replace tag with contents, including children"""
        children = list(self.iterchildren(reversed=True))
        if not len(children):
            self.string_replace(self.text)
        else:
            parent = self.getparent()
            my_index = parent.index(self)
            last_child = children[-1]
            last_child.tail = self.textjoin(last_child.tail, self.tail)
            parent = self.add_to_previous(self.textjoin(self.text, self.tail))
            for child in children:
                parent.insert(my_index, child)

    def string_replace(self, replacement):
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
        """Join a and b, replacing either one with an empty string
        if that one is not truthy."""
        return ''.join([(a or ''), (b or '')])
