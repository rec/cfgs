#!/usr/bin/env python

import sys
from docutils.core import publish_string


def make(input, output):
    with open(input) as i, open(output, 'wb') as o:
        p = publish_string(i.read(), writer_name='html')
        o.write(p)


if __name__ == '__main__':
    make(*sys.argv[1:])
