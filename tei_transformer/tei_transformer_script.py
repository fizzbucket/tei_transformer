import argparse
import os
import shutil
from tei_transformer.transform import transform_to_pdf

def get_args():
    parser = argparse.ArgumentParser(
        description="Transform a TEI-encoded critical edition into a pdf.")
    parser.add_argument("--newproject",
                        help="Create new project.",
                        action="store_true")
    parser.add_argument("-t", "--transform",
                        help="TEI file to transform")
    parser.add_argument("-o", "--outputname",
                        help="Filename of the transformed file.",
                        default=None)
    parser.add_argument("-f", "--force",
                        help="Force recompilation of a latex file,\
                         even if unchanged.",
                        action="store_true")
    parser.add_argument('-q', '--quiet',
                        help="Run quietly",
                        action="store_true")
    return parser.parse_args()


def make_new_project():

    resourcespath = os.path.join(os.curdir, 'resources')
    basepath = os.path.dirname(os.path.abspath(__file__))
    examplespath = os.path.join(basepath, 'examples')

    try:
        assert not os.path.exists(resourcespath)
        os.mkdir(resourcespath)
    except AssertionError:
        print('%s already exists.' % resourcespath)
        exit()

    examples_list = ['introduction.tex',
                    'personlist.xml',
                    'references.bib',
                    'config.py',
                    'custom_teitag.py',
                    '__init__.py']

    for x in examples_list:
        inpath = os.path.join(examplespath, x)
        outpath = os.path.join(resourcespath, x)
        shutil.copy(inpath, outpath)


def main():
    args = get_args()
    if args.newproject:
        make_new_project()
    if args.transform:
        transform_to_pdf(args)

if __name__ == '__main__':
    main()
