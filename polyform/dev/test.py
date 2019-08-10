#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
# pylint: disable=all
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Used for internally testing functions.
"""

import os
import sys
import re
import doctest
import importlib
from pylint import epylint as lint
from ..util import osu
from ..util.out import debug, notify, header, error, abort # pylint: disable=unused-import

def poly(context): # poly=None, name=None, path=None):
    """
    Test a function, by running doctests, linter and _test version if it exists
    """

    options = ()
#    if os.path.exists(".pylintrc"):
#        cwd = os.getcwd()
#        options=("--rcfile=" + os.path.join(cwd, ".pylintrc"),)

    name = context['func']
    header("Testing {}", name)
    # NOTE: this will not capture any {function}.py
    for root, _, files in os.walk(name):
        for fname in files:
            as_file(root, fname, options=options)

def as_module(root, modname, options=()):
    """
    Run doctests and linter on given file.
    """
#    print("MODULE")
    path = os.path.join(*modname.split("."))
    if os.path.exists(path + ".py"):
        modfile = path + ".py"
    elif os.path.exists(os.path.join(path, "__init__.py")):
        modfile = os.path.join(path, "__init__.py")
    else:
        raise ValueError("Cannot find module file for " + modname)

    _test(root, modfile, modname, options=options)

def as_file(root, modfile, options=()):
    """
    Run doctests and linter on given file.
    """
#    print("FILE")
    if modfile[-3:] != ".py":
        return
    modfile = os.path.join(root, modfile)
    if not os.path.exists(modfile):
        raise ValueError("Cannot find file for module " + modfile)
    modname = modfile[:-3]
    modname = re.sub(os.path.sep + "__init__", "", modname)
    modname = re.sub(os.path.sep, ".", modname)
    _test(root, modfile, modname, options=options)

def _test(root, modfile, modname, options=()):
#    print("TEST ({}, {}, {}, {})".format(root, modfile, modname, options))
    options = ()
    if os.path.exists(".pylintrc"):
        cwd = os.getcwd()
        options += ("--rcfile=" + os.path.join(cwd, ".pylintrc"),)
    header("Linter on {}", modname).flush()
    if lint.lint(modfile, options=options) > 0:
        sys.exit(1)
    header("Doctest on {}", modname).flush()
    module = importlib.import_module(modname)
    try:
        failed, total = doctest.testmod(module, optionflags=doctest.ELLIPSIS)
    except:
        import traceback
        traceback.print_exc()
        raise

    notify("    {} tests, {} failures", total, failed)
    if failed:
        sys.exit(1)
