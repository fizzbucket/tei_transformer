Introduction
============

tei_transformer is a Python script for transforming a TEI-encoded critical edition into a pdf file. There are plenty of XSLT stylesheets to do something like this already, but using Python instead gives a secret advantage: we don't really lose out on anything, but it's unbelievably easy to customise things. We also don't have to restrict ourselves to the xml tree; it's very easy to bring in extra information or shift things about more easily. For example, a trick like adding a lemma note from an external data source for a person mentioned in the edition on their first appearance, then only indexing them on subsequent ones, is trivially easy rather than enormously complicated.

Basic Usage
___________

::

	tei_transformer example.xml

This is pretty simple. The one proviso is that the script expects a folder called ``resources`` in the same directory as example.xml. This needs to contain a file called ``personlist.xml`` containing a list (in TEI-format) of people mentioned in the text and a BibLaTex file of references for citations called ``references.bib``.

There's also plenty of optional files you can include for things like introductions. You can change things like the filenames of these by providing a file ``config.yaml'' in resources.

Of course, it's also possible to skip all of this; and fit it into your own chain of events; simply getting a .tex file is as simple as::
	
	from tei_transformer.transform import ParserMethods

	xmlpath = 'example.xml'
	tree = ParserMethods.parse(xmlpath)
	transformed_tree = ParserMethods.transform_tree(tree)


However, your project's assumptions and requirements will almost certainly differ from the default assumptions, and it's definitely a good idea to muck about with things and see what happens. See :ref:`customisation`, or consider just downloading the very simple source and manipulating it as you choose.

Installation
_____________

::

	pip install tei_transformer

Requirements
_____________

Files are parsed using lxml::

	pip install lxml

The tex file produced needs pdflatex[http://latex-project.org/ftp.html] to produce a pdf file. The installation of tex which you use will also need the ``reledmac`` package and the Perl script ``latexmk``. Most installations will have these in any case.

