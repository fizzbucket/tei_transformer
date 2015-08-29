.. _customisation:

Customisation
=============

The nature of a critical edition is such that you'll almost certainly have your own special requirements; and the nature of a TEI-encoding scheme is such that things are so very diverse it's hard to make any assumptions about how an encoding works.

Because of this, you are very likely to want to either give new instructions for transforming a particular type of tag, or override the existing ones to meet your own requirements.

Fortunately, the whole reason this project exists is to make it very easy to do so.

How things work
________________

We use a standard parser, lxml, to make sense of a tei-encoded lxml file. This parser reads tags according to a Python class, TEITag. Each type of tag (``p``, ``head``, ``q``, etc) is assigned to a class inheriting from TEITag which defines a property, ``target`` that is the same as the tag's name, and also gives a method ``get_replacement``, which is called to replace the tag in the new document with a string.

If the replacement is ``None``, a tag is not replaced.

This seems quite complicated -- and it can get as complicated as you like -- but its usage is very simple. Here is, for example, the complete class ``SoCalled``, which handles tags of the type ``<soCalled>``

.. code-block:: python

	class SoCalled(TEITag):
    	
    	target = 'soCalled'

    	def get_replacement(self):
        	return "`%s'" % self.text

The only point which might need explanation is where ``self.text`` comes from; it is, of course, the text contained within the tag. Because the class SoCalled inherits from the class ``TEITag``, and ``TEITag`` inherits from the class ``LXML.etree.ElementBase``, all the methods available to ``ElementBase`` can be called to find out more about the tag. See the API documentation under ``TEITag`` to see what is available. These mean that any information from within the parse tree you want to find out is easily accessible.

For example, getting the attribute 'rend' for a tag is as simple as::

	self.get('rend')

There is one proviso, though: unlike XSLT, tags are replaced one-at-a-time, rather than simultaneously. To make this a bit more logical, tags are not replaced in document order, but, weakly-sorted, by the number of descendants.

So you can always guarantee that a tag's parent is still accessible (with ``self.getparent()``), but its children or siblings may have already been replaced with text.

Several methods are also available for tags beyond those defined by lxml.etree; again, see the API documentation. The big ones are ``unwrap()``, which unwraps a tag, and ``delete()``, which removes it without replacement.

Overriding an existing class, or adding a new one
_________________________________________________

So you don't agree with the way a tag is processed?

Or you want to use a tag that doesn't have a handling class?

Cool cool cool.

Just save a new file, ``custom_teitag.py`` in the ``resources`` directory. Then add whatever new classes you want in there. They'll be automagically included, and if their target is already defined by another class, they'll override that one, and we can all carry on happily.

