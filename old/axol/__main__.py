from argparse import ArgumentParser

import axol.crawl
import axol.report
import axol.adhoc


def main():
    p = ArgumentParser()
    sp = p.add_subparsers(dest='mode')
    cp = sp.add_parser('crawl')
    axol.crawl.setup_parser(cp)
    rp = sp.add_parser('report')
    axol.report.setup_parser(rp)
    ap = sp.add_parser('adhoc')
    axol.adhoc.setup_parser(ap)

    args = p.parse_args()
    if args.mode == 'crawl':
        axol.crawl.run(args)
    elif args.mode == 'report':
        axol.report.run(args)
    elif args.mode == 'adhoc':
        axol.adhoc.run(args)
    else:
        raise RuntimeError(args.mode)


if __name__ == '__main__':
    main()
