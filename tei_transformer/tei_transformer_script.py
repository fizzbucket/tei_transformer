import argparse
from tei_transformer import transform


def get_args():
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
    return parser.parse_args()


def main():
    args = get_args()
    if args.transform:
        transformer = transform.TransformToPDF(
            args.transform,
            args.outputname,
            args.force,
            args.quiet
            )
        transformer.transform()

if __name__ == '__main__':
    main()
