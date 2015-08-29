Introduction
============

tei_transformer is a Python script for transforming a TEI-encoded critical edition into a pdf file. There are plenty of XSLT stylesheets to do something like this already, but using Python instead gives a secret advantage: we don't really lose out on anything, but it's unbelievably easy to customise things. We also don't have to restrict ourselves to the xml tree; it's very easy to bring in extra information or shift things about more easily. For example, a trick like adding a lemma note from an external data source for a person mentioned in the edition on their first appearance, then only indexing them on subsequent ones, is trivially easy rather than enormously complicated.

Basic Usage
___________

::

	tei_transformer --new-project
	tei_transformer --transform example.xml

``new-project`` creates a directory in the current one named ``working_directory`` containing ancillary resources. It is expected that there will be a file called ``personlist.xml`` containing a list (in TEI-format) of people mentioned in the text, a BibLaTex file of references for citations called ``references.bib``, and an introduction in LaTeX format named ``introduction.tex``. Once those are filled out, calling with the ``transform`` argument creates a pdf.

Of course, it's also possible to skip all of this; and fit it into you own chain of events; simply getting a .tex file is as simple as::
	
	from tei_transformer.XMLProcessingWrapper import xml_to_tex

	xmlpath = 'example.xml'
	tex = xml_to_tex(xmlpath)


However, your project's assumptions and requirements will almost certainly differ from the default assumptions, and it's definitely a good idea to muck about with things and see what happens. See :ref:`customisation`, or consider just downloading the very simple source and manipulating it as you choose.

Installation
_____________

::

	pip install tei_transformer

Requirements
_____________

Files are parsed using lxml::

	pip install lxml

The tex file produced needs pdflatex[http://latex-project.org/ftp.html] to produce a pdf file. The installation of tex which you use will also need the ``reledmac`` package, and ``latexmk`` is a good idea. Most installations will have these in any case.

