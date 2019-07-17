from argparse import ArgumentParser

import axol.crawl
import axol.report


def main():
    p = ArgumentParser()
    sp = p.add_subparsers(dest='mode')
    cp = sp.add_parser('crawl')
    rp = sp.add_parser('report')
    axol.report.setup_parser(rp)
    args = p.parse_args()
    if args.mode == 'crawl':
        raise NotImplementedError
    elif args.mode == 'report':
        axol.report.run(args)
    else:
        raise RuntimeError(args.mode)

if __name__ == '__main__':
    main()
