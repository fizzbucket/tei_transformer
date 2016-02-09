import argparse
from tei_transformer.transform import transform_tei
import sys


def get_args(args):
    parser = argparse.ArgumentParser(
        description="Transform a TEI-encoded critical edition into a pdf.")
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
    parser.add_argument('-s', '--standalone',
                        help="Do not include introduction or appendices",
                        action="store_true")
    return parser.parse_args(args)

def interpret_args(args):
    if args.transform:
        transform_tei(
            args.transform,
            outname=args.outputname,
            force=args.force,
            quiet=args.quiet,
            standalone=args.standalone
            )

def main():
    args = get_args(sys.argv[1:])
    interpret_args(args)

if __name__ == '__main__':
    main()
