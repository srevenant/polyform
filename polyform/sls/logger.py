#!/usr/bin/env python3
# not: /app/local/bin/virtual-python
# vim modeline (put ":set modeline" into your ~/.vimrc)
# vim:set expandtab ts=4 sw=4 ai ft=python:
# pylint: disable=superfluous-parens

import os
import sys
import json
import time
import logging
import logging.config
import datetime
import traceback

################################################################################
class Logger(logging.StreamHandler):
    """
    A handler class which allows the cursor to stay on
    one line for selected messages
    """
    on_same_line = False

    ############################################################################
    def configure(self, *args):
        """do not want"""

    ############################################################################
    def emit(self, record):
        """Overriding emit"""
        try:
            msg = record.msg.strip()
            log(msg)
        except (KeyboardInterrupt, SystemExit):
            raise
        except: # pylint: disable=bare-except
            self.handleError(record)

    ############################################################################
    # pylint: disable=redefined-builtin
    def format(self, record):
        return record.msg.decode()

###############################################################################
def log(*args, **kwargs):
    """
    Log key=value pairs for easier bigdata processing

    test borked
    x>> log(test="this is a test", x='this') # doctest: +ELLIPSIS
    - - [...] test='this is a test' x=this
    """
    # args = (datetime.datetime.now().replace(microsecond=0).isoformat(),) + args
    tstamp = datetime.datetime.now().replace(microsecond=0).isoformat()
    if args:
        kwargs["_args"] = list(args)

    try:
        sys.stdout.write(tstamp)
        sys.stdout.write(" ")
        for key, value in kwargs.items():
            sys.stdout.write("{}={} ".format(key, json.dumps(value)))
        sys.stdout.write("\n")
        sys.stdout.flush()
    except Exception: # pylint: disable=broad-except
        print("LOGGING FAILURE")
        print("ARGS={}\nKWARGS={}".format(args, kwargs))
        traceback.print_exc()
