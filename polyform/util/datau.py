#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Various data processing utilities for Polyforms
"""

import json
import base64

def flat_list(*args):
    """
    >>> flat_list()
    []
    >>> flat_list([])
    []
    >>> flat_list("one")
    ['one']
    >>> flat_list(("one", "two"))
    ['one', 'two']
    >>> flat_list("one", "two")
    ['one', 'two']
    >>> flat_list(["one"])
    ['one']
    >>> flat_list(["one", "two"])
    ['one', 'two']
    >>> flat_list(["one", "two"], "three")
    ['one', 'two', 'three']
    >>> flat_list(["one", "two"], ["three"])
    ['one', 'two', 'three']
    """
    out = list()
    for item in args:
        if isinstance(item, (list, tuple)):
            out.extend(flat_list(*item))
        else:
            out.append(item)
    return out

def serialize(data):
    """
    serialize data for the CLI

    >>> serialize({"a":"b"})
    'eyJhIjogImIifQ=='
    """
    return base64.b64encode(json.dumps(data).encode()).decode()

def deserialize(serialized):
    """
    deserialize data for the CLI

    >>> deserialize('eyJhIjogImIifQ==')
    {'a': 'b'}
    """
    return json.loads(base64.b64decode(serialized))
