#!/usr/bin/env python
# coding=utf-8


import argparse
import json
from urllib2 import urlopen

from nagiosplugin import ScalarContext, Metric, guarded, Check, Resource


class NginxUpstreams(Resource):
    def __init__(self, status, upstreams):
        self.status = status
        self.upstreams = dict((upstream, {'up': 0, 'down': 0}) for upstream in upstreams)

    def probe(self):
        for server in self.status['servers']['server']:
            if server['status'] == 'up':
                self.upstreams[server['upstream']]['up'] += 1
            else:
                self.upstreams[server['upstream']]['down'] += 1

        return [Metric(name, 100 * servers['down'] / (servers['up'] + servers['down']))
                for name, servers in self.upstreams.items()
                ]


@guarded
def main():
    parser = argparse.ArgumentParser(
        description='Check nginx upstreams via nginx_upstream_check_module'
    )
    parser.add_argument('-u', '--url', required=True,
                        help='url to check (output must be json-formatted)')
    parser.add_argument('-c', '--critical', default=49,
                        help='Critical threshold for number '
                             'of DOWN upstreams (in percent)')
    parser.add_argument('-w', '--warning', default=25,
                        help='Warning threshold for number '
                             'of DOWN upstreams (in percent)')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='increase output verbosity (use up to 3 times)')
    args = parser.parse_args()

    status = json.loads(urlopen(args.url).read())
    upstreams = set(server['upstream'] for server in status['servers']['server'])
    contexts = (ScalarContext(
        upstream,
        critical=args.critical,
        warning=args.warning,
        fmt_metric='{value} % servers are down in {name} upstream'
    ) for upstream in upstreams)

    check = Check(NginxUpstreams(status, upstreams), *contexts)
    check.main(args.verbose, timeout=60)


if __name__ == '__main__':
    main()
