#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved

Argparser helper w/Cli object
"""

import os
import sys
import argparse
from ..util.out import debug, notify, header, error, abort # pylint: disable=unused-import

################################################################################
def syntax(*errmsg, args=None):
    """Abort with a syntax error"""
    if args:
        cmd = os.path.basename(sys.argv[0])
        notify("usage: {} {}\n", cmd, args)
    abort(errmsg)

def argparse_class_methods(obj_class, obj_instance, prefix):
    """
    Create an argparser, with subparsers based on
    methods on class matching prefix.  Example:

        argparse_class_methods(MyCli, mycli, "cmd_*")
    """
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    def set_parser(obj_class, action, method):
        meta = getattr(obj_class, method)
        doc = meta.__doc__
        sub = subparsers.add_parser(action, help=doc)
        sub.set_defaults(func=getattr(obj_instance, method))
        # add doc / option parsing here, for now, just nargs
        sub.add_argument("args", nargs="*")

    # global_args = list()
    prefix_len = len(prefix)
    for method in obj_class.__dict__:
        if method[:prefix_len] == prefix:
            action = method[prefix_len:].replace("_", "-")
            set_parser(obj_class, action, method)

    return parser
