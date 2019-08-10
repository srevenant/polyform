#!/usr/bin/env python3
"""
Run lint and doctests on all python files in `polyform` module
"""

import os
import sys
import argparse
import doctest
import importlib
from pylint import epylint as lint
import re

from polyform.util import osu
import polyform.dev.test as test

def main():
    """ .. main .. """
    parser = argparse.ArgumentParser()
    parser.add_argument("modules", help="Only one file/module", nargs="*")
    args = parser.parse_args()

    if args.modules:
        for mod in args.modules:
            try:
                test.as_module(".", mod)
            except ValueError:
                try:
                    test.as_file(".", mod)
                except ValueError:
                    sys.exit("Unable to find file/module: " + mod)
    else:
        for root, _, files in os.walk("polyform"):
            for fname in files:
                test.as_file(root, fname)

if __name__ == '__main__':
    main()
