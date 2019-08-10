#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

General variants of output (std or error)
"""

import os
import sys

def debug(msg, *args, obj=None, **kwargs):
    """
    If os environ DEBUG is set to anything, send a debug message, formatted using args.
    """
    if os.getenv('DEBUG'):
        if args:
            msg = msg.format(*args, **kwargs)
        if obj:
            msg = "{} ".format(obj) + msg
        sys.stderr.write(msg)

def notify(msg, *args, **kwargs):
    """
    Variant print, allowing us to override and control output better, and
    with an implicit .format() call for ease of use.

    Return FD written to so we can flush it, if so desired.

    >>> notify("test {}", 10)
    test 10
    <doctest._SpoofOut object at ...>
    >>> notify("test {}", 10).flush()
    test 10
    """
    if args or kwargs:
        msg = msg.format(*args, **kwargs)
    sys.stdout.write(msg)
    sys.stdout.write("\n")
    return sys.stdout

def error(msg, *args, **kwargs):
    """
    Variant like print, but for stderr
    """
    sys.stderr.write(msg.format(*args, **kwargs) + "\n")
    return sys.stderr

def header(msg, *args, **kwargs):
    """
    Variant prints, allowing us to override and control output better
    Return FD written to so we can flush it, if so desired.
    """
    sys.stdout.write("\n==> " + msg.format(*args, **kwargs) + "\n")
    return sys.stdout

def abort(msg, *args, **kwargs):
    """
    Abort with a message, format using args.
    """
    if args:
        msg = msg.format(*args, **kwargs)
    sys.exit(msg)
