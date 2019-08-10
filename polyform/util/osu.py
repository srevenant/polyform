#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Operating system utilities.  General improvements over what is available in `os`
"""

import os
import sys
import json
import subprocess

from .out import debug

############################################################
# pylint: disable=inconsistent-return-statements
def getcmd(command):
    """
    Locate a command in our path

    >>> getcmd("ls")
    '/bin/ls'
    """
    path = os.getenv('PATH')
    for part in path.split(os.path.pathsep):
        path = os.path.join(part, command)
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    exit("Unable to find '" + command + "' in your path!")

############################################################
def must_chdir(path):
    """
    Lame wrapper to try to verify if the chdir really worked or not...
    Assertion is if the folder didn't change, the chdir failed.
    This isn't true, if you are chdiring to your current folder...

    >>> cwd = os.getcwd()
    >>> os.chdir("/tmp")
    >>> must_chdir(cwd)
    True
    >>> must_chdir(cwd)
    Traceback (most recent call last):
    ...
    OSError: Unable to chdir(...)
    """
    cwd = os.getcwd()
    os.chdir(path)
    if cwd != os.getcwd():
        return True
    raise OSError("Unable to chdir({})".format(path))

############################################################
def exc(args):
    """
    Exec a system command, replacing this process with that command (we go away)
    Handier than exec()
    """
    debug("\n>>>")
    arg0 = True
    for arg in args:
        if arg0:
            arg = os.path.basename(arg)
            arg0 = False
        if " " in arg:
            arg = json.dumps(arg) # easy way to get quoting right
        debug(" " + arg)
    debug("\n\n")
    os.execv(args[0], args)

############################################################
def cmd(command, abort=False): # pylint: disable=redefined-outer-name
    """
    Run a system command, and return the status.  If you want the output,
    call cmd_out()

    If a list is presented, run it directly (safer).
    If a string is presented, run it via the shell

    >>> cmd("ls /dev/null")
    True

    >>> cmd(["ls", "/dev/null"])
    True
    """

    sys.stdout.flush()
    sys.stderr.flush()
    if isinstance(command, list):
        shell = False
    else:
        shell = True
    debug("cmd(shell={})>>> {}\n", shell, command)
    sub = subprocess.call(command, shell=shell)
    sys.stdout.flush()
    sys.stderr.flush()
    if sub > 0:
        if abort:
            sys.exit(sub)
        return False
    return True

def cmdx(command):
    """like cmd(), but abort if there is an error."""
    return cmd(command, abort=True)

############################################################
def cmd_out(command, abort=False): # pylint: disable=redefined-outer-name
    """
    Like cmd(), run a system command, but return the output

    >>> cmd_out("ls /dev/null")
    (True, '/dev/null\\n')

    >>> cmd_out(["ls", "/dev/null"])
    (True, '/dev/null\\n')
    """

    sys.stdout.flush()
    sys.stderr.flush()
    if isinstance(command, list):
        shell = False
    else:
        shell = True
    debug("cmd(shell={})>>> {}\n", shell, command)
    sub = subprocess.Popen(command, stdout=subprocess.PIPE, shell=shell)
    sys.stdout.flush()
    sys.stderr.flush()
    output, _err = sub.communicate()
    output = output.decode() # grr bytes object
    if sub.returncode > 0:
        if abort:
            sys.exit(output)
        return (False, output)
    return (True, output)

def cmd_outx(command):
    """like cmd_out(), but abort if there is an error."""
    return cmd_out(command, abort=True)

def needs_folder(path):
    """make sure a folder structure exists, ala `mkdir -p`, without erroring"""
    if not os.path.exists(path):
        os.makedirs(path)
