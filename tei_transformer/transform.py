import subprocess
import re
from functools import partial

from .parser import Parser, transform_tree
from .pathsmanager import pathmanager
from .config import config
from .persdict import persdict


def transform_tei(inputname, outname=None,
                  force=False, standalone=False):
    """"Read inputname and transform to a pdf"""
    inputpaths, textwraps, workfiles = pathmanager(inputname, outname, standalone)
    bare_text = transform(*inputpaths)
    latex = latexify(bare_text, *textwraps)
    make_pdf(latex, *workfiles, force)


def transform(inputpath, personlistpath):
    _persdict = persdict(personlistpath)
    body = Parser(inputpath).getroot().find('.//{*}body')
    assert body is not None
    tree = transform_tree(body, _persdict)
    return '\n'.join(tree.itertext()).strip()


def latexify(bare_text, before, after):
    text = '\n'.join([before, bare_text, after])
    for fix in config['string_replacements']:
        text = text.replace(*fix)
    for fix in config['regex_replacements']:
        text = re.sub(*fix, text)
    return text


def make_pdf(latex, working_tex, working_pdf, out_pdf, force):

    missing = not working_pdf.exists() or not working_tex.exists()
    if force or missing or hash(working_tex.text()) != hash(latex):
        working_tex.write_text(latex)
        call_cmd = config['caller_command']
        latexmk = '{c} {w}'.format(c=call_cmd, w=working_tex).split()
        subprocess.call(latexmk)
    working_pdf.copy(out_pdf)
