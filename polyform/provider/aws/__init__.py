#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Basic AWS bits
"""

import os

def aws_trap(label, func, *args, **kwargs):
    """
    wrap a function call and catch common errors from boto3
    """
    try:
        return func(*args, **kwargs)
    except Exception as err: # pylint: disable=broad-except
        errname = err.__class__.__name__ # boto3 error handling is painful
        if errname == 'ResourceNotFoundException':
            print("{} doesn't exist".format(label))
        elif errname == 'ResourceInUseException':
            print(err)
        elif errname == 'AttributeError':
            print("{} is still deleting".format(label))
        elif errname == 'EntityAlreadyExistsException':
            print("{} is already created".format(label))
        elif errname == 'BucketAlreadyOwnedByYou':
            print("{} is already created".format(label))
        elif errname == 'NoSuchEntityException':
            pass
        else:
            print(errname)
            raise
