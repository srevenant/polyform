#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Inception - running functions inside the container from outside, to help
build and manage our layers, testing, and development.
"""

import os
import sys
import time
# import hashlib
from . import ENTRY # so we can print what method we are coming in on
from ..util import datau, osu
from ..util.out import debug, notify, header, error, abort # pylint: disable=unused-import

def to_zip(dstdir=None, fname=None, ver=None, srcdir=None, src=None):
    """
    Create a zipfile of a given folder, and link it to "latest"
    """
    os.chdir("/tmp") # so we are not in /_deps or /var/task, and osu.must_chdir will work
    zipfile = dstdir + "/" + fname.format(ver)
    if os.path.exists(zipfile):
        header("Using cache for {}", zipfile)
    else:
        header("Zipping " + zipfile)
        osu.must_chdir(srcdir)
        osu.cmd(["zip", "-q", "--exclude", "*.pyc", "-r9", zipfile, src])

    osu.must_chdir(dstdir)
#    header("Linking " + fname.format(ver) + " -> " + fname.format("latest"))
    osu.cmd(["ln", "-sf", fname.format(ver), fname.format("latest")])

def export_zips(context):
    """
    Create zipfiles of the various layers to this function
    """
    base = "/_build/" + context['func']
    osu.needs_folder(base)

    # libs first
    if not os.path.exists("/_deps/.cksum"):
        abort("Missing /_deps from within the container, correct image?")

    with open("/_deps/.cksum") as infile:
        cksum = int(infile.read())

    osu.cmd(["rsync", "-a", "--exclude", "*.pyc",
             os.environ["POLYFORM_INCEPT"] + "/.", "/_deps/python/."])
    to_zip(dstdir=base, fname="libs.{}.zip", ver=cksum, srcdir="/_deps", src="python")

    # then function
    ttime = int(time.time() * 1000)
    to_zip(dstdir=base, fname="func.{}.zip", ver=ttime, srcdir="/var/task", src=".")

def test_poly(context):
    """Shunt over to the testing module"""
    from . import test
    test.poly(context)

if __name__ == "__main__":
    DATA = datau.deserialize(sys.argv[1])
    header("Running polyform.{}.{}()".format(ENTRY, DATA['exec']))
    globals()[DATA['exec']](DATA)
