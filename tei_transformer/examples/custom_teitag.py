from tei_transformer.teitag import TEITag

# Add custom tag processing classes here.
# They should inherit TEITag; by doing so they will inherit all the methods of lxml.etree.ElementBase.
# They should define a property, target, that shows the name of tags they ought to handle. This will catch tags of this type automatically on parsing.
# They should also define a method, get_replacement, that returns a string the tag ought to be replaced with, which will be called later on.
# They should *not* define an __init__ method. An _init is a possible substitute, but it is impossible to guarantee that it will not be called more than once.
# Other than these restrictions, do what you like.

# A class defined here with a target defined already in the core program will be overridden by this replacement.

# Example:

# class FakeTag(TEITag):
#	target = 'fakeTag'
#
#	def get_replacement(self):
#		return self.text