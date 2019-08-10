#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:

"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Create boilerplate files and directories
"""

import os
import sys
from .. import config
from ..util.out import debug, notify, header, error, abort # pylint: disable=unused-import
# from . import config
#
# def default_config(name):
#     """
#     using the config.py classes, create a default structure
#     """
#     print(name)

def new(name):
    """
    Create boilerplate files and directories
    """
    errors = 0
    for notfile in ("Polyform.yml", "src/" + name + "/__init__.py", ".gitignore"):
        if os.path.exists(notfile):
            errors = errors + 1
            error("ERROR: " + notfile + " already exists!")
    if errors > 0:
        sys.exit(1)

    def outfile(fname, content):
        dirname = os.path.dirname(fname)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)

        if os.path.exists(fname):
            error("ERROR: " + fname + " already exists!")
        with open(fname, "w") as filed:
            filed.write(content)
        header("Created " + fname)

    # pylint: disable=protected-access
    skel = config.ParseObj._skeleton(config.Polyform)
    skel['forms'][name] = skel['forms']['form-name']
    del skel['forms']['form-name']
    outfile("Polyform.yml", config.to_yaml(skel))
    outfile("src/" + name + "/__init__.py", """#!/usr/bin/env python3
#$#HEADER-START
# vim:set expandtab ts=4 sw=4 ai ft=python:
#$#HEADER-END
\"\"\"
Module Description Here
\"\"\"
from polyform.sls.decorators import aws_lambda_polyform, Result

@aws_lambda_polyform
def train(context):
    \"\"\"function doc\"\"\"
    return Result(detail="here")

@aws_lambda_polyform
def predict(context):
    \"\"\"function doc\"\"\"
    return Result(detail="here")
""")
    outfile(".gitignore", """
deps
_build
.*.swp
*.py[cod]
__pycache__
pylibs
.DS_Store
/**/node_modules
""")
    outfile(".pylintrc", """
[MESSAGES CONTROL]
disable=missing-docstring
""")
