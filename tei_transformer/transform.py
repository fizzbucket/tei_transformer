from .XMLProcessingWrapper import xml_to_tex
import subprocess
import sys
import os
import shutil
import filecmp
import hashlib

def transform_to_pdf(arguments):
    global args
    args = arguments
    working_directory = os.path.join(os.curdir, 'working_directory')
    check_requirements(working_directory)
    make_latex(working_directory)

def check_run(texpath, tex):
    if not args.force:
        if os.path.exists(texpath):
            with open(texpath, 'rb') as exists:
                exists = exists.read()
            existing_hash = hashlib.md5(exists).digest()
            new_hash = hashlib.md5(tex.encode('utf8')).digest()
            return existing_hash == new_hash
    return False

def make_latex(working_directory):
    basename = args.transform[:args.transform.find('.')]
    texname =  basename + '.tex'
    texpath = os.path.join(working_directory, texname)
    working_pdf = os.path.join(working_directory, basename + '.pdf')
    tex = xml_to_tex(args.transform, working_directory=working_directory, persdict=True)
    
    if not check_run(texpath, tex):
        with open(texpath, 'w') as texw:
            texw.write(tex)
        result = call_latex(texpath)
    else:
        print('Has not changed since the last run.')
    
    if not args.outputname:
        args.outputname = basename + '.pdf'
    shutil.copy(working_pdf, args.outputname)

def check_requirements(outputdir):

    if not os.path.exists(outputdir):
        os.mkdir(outputdir)

    resources_dir = os.path.join(os.curdir, 'resources')
    resource_files = ['references.bib',
                      'personlist.xml',
                      'introduction.tex']

    for name in resource_files:
        inputpath = os.path.join(resources_dir, name)
        assert os.path.isfile(inputpath)
        outputpath = os.path.join(outputdir, name)
        if not os.path.isfile(outputpath):
            shutil.copy2(inputpath, outputpath)
        elif not filecmp.cmp(inputpath, outputpath):
            shutil.copy2(inputpath, outputpath)
            if name == 'personlist.xml':
                picklepath = os.path.join(outputdir,
                                        'personlist.pickle')
                if os.path.isfile(picklepath):
                    os.unlink(picklepath)

    # Add config file so that latexk knows to call makeglossaries
    if not os.path.isfile('.latexmkrc'):
        latexmkrc = '\n'.join([
        "add_cus_dep( 'glo', 'gls', 0, 'makeglossaries' );",
        "sub makeglossaries {",
        'system( "makeglossaries \\"$_[0]\\"" );',
        '}',])
        with open('.latexmkrc', 'w') as lm:
            lm.write(latexmkrc)


    basename = args.transform[:args.transform.find('.')]
    index_style_path = os.path.join(outputdir, basename + '.mst')

    # Add some information on how to style indices.
    if not os.path.isfile(index_style_path):
        index_style = '\n'.join(['headings_flag 1',
            'heading_prefix "{\\\\bfseries "',
            'heading_suffix "}\\\\nopagebreak\\n"',
            ])
        with open(index_style_path, 'w') as isty:
            isty.write(index_style)


def call_latex(texpath):
    options = ['-bibtex', # run biber for references
               '-cd', # change to working_directory to run
               '-f', # force through errors
               '-g', # run even if unchanged.
               '-pdf',]
    latexmk_command = ['latexmk'] + options + [texpath]
    if args.quiet:
        with open(os.devnull, "w") as fnull:
            return subprocess.call(latexmk_command, stdout = fnull, stderr = fnull)
    return subprocess.call(latexmk_command)
