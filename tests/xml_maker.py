import textwrap

xmlns = 'xmlns="http://www.tei-c.org/ns/1.0"'

xml_head = textwrap.dedent("""<?xml version="1.0" encoding="UTF-8"?>
                            <TEI %s>
                            <text>
                            <body>""" % xmlns)
xml_foot = textwrap.dedent("""</body>
                            </text>
                            </TEI>
                            </xml>""")

person_template = textwrap.dedent("""\
    <person xml:id="{xmlid}">
     <persName>
      <forename>
       {forename}
      </forename>
      <addName>
       {addName}
      </addName>
      <surname>
       {surname}
      </surname>
     </persName>
     <birth>
      {birth}
     </birth>
     <death>
      {death}
     </death>
     <trait type="description">
      <p>
      {description}
      </p>
     </trait>
    </person>""")

def xml_maker(text, head=xml_head, foot=xml_foot):
    return '\n'.join([head, text, foot])

def broken_xml():
    text = "<p>Hello <q>world</p></q>"
    return xml_maker(text)

def perslist_maker(text):
    head = '<personList %s>' % xmlns
    foot = '</personList>'
    return xml_maker(text, head, foot)

def person_maker(**kwargs):
    return perslist_maker(person_template.format(**kwargs))

