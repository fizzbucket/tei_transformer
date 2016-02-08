#About

tei_transformer is a Python script for transforming a TEI-encoded critical edition into a pdf file. There are plenty of XSLT stylesheets to do something like this already, but using Python instead gives a secret advantage: we don't really lose out on anything, but it's unbelievably easy to customise things.

So what we have here is conceptually as much a framework for your own changes as something immediately usable (although it is.)

# Installation

pip3 install tei_transformer

# Simple usage

	from tei_transformer import transform

	xmlpath = 'example.xml'
	transformer = transform.TransformToPDF()
	transformer.transform()
	

# Complete toolchain

	tei_transformer --transform example.xml

# Interested?

[Read the docs](http://tei-transformer.readthedocs.org/en/latest/index.html) for more.



