#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Inception - running functions inside the container from outside, to help
build and manage our layers, testing, and development.
"""

#import os
import json
from dictlib import Dict #, dug
from .reflex_arc import dex_intersect, DEXError
from ..gql import validate as gql_validate
#from . import reflex_arc

# for now just use Dict, eventually make this a class that sls methods can return
Result = Dict

class DataExpectationFailed(Exception):
    """External error"""

# pylint: disable=too-many-instance-attributes
class PolyformDecorator():
    """
    Decorator for polyform functions.  May also be derived.

    Other classes should derive from this class, to create specialized decorators.

    Arguments:
        train (function): a training function to call, if one is needed
    """
    dims = None # explicit dimensions
    faas = None
    _args = None
    _kwargs = None
    _func = None
    _cfg = None
    _form = None
    _interface = None

    def __init__(self, func, *args, **kwargs): # pylint: disable=unused-argument
        self._func = func
        self._interface = Dict(event=None, biome=None)
        self.dims = Dict(model=dict(trained=None, csv=None))
        if kwargs.get('faas') == 'lambda':
            self.faas = 'lambda'
        else:
            raise TypeError("Polyform faas type is unknown, look for: @PolyformDecorator(faas=?)")
        self._args = args
        self._kwargs = kwargs

    def __call__(self, *args, **kwargs):
        """
        A polyform wraper, for some convenience steps
        """
        try:
            with open("_polyform.json") as infile:
                self._cfg = Dict(json.load(infile))
            # TODO NEXT: AUTHENTICATE

            context = self.gather(*args, **kwargs)
            print("==> Calling Function")
            result = self._func(context=context, dims=self.dims)
            if not isinstance(result, Result):
                raise DataExpectationFailed("function returned a non Result() object")
            return self.finish(context, result)
        except DEXError as err:
            raise DataExpectationFailed(err.message)

    def gather(self, *args, **kwargs):
        """
        future: this will pull in from the core
        """
        print("==> Starting DEX Gather")

        self._form = self._cfg.forms[self._cfg.target]
        self._interface = self._form.interface

        # if os.environ.get('POLYTEST'):
        #     form = self._cfg.forms[self._cfg.target]
        #     if form.test:
        #         if not os.path.exists(form.test.input.file):
        #             raise FileNotFoundError("No such file or directory: " + form.test.input.file)
        #         print("==> Using test data")
        #         with open(form.test.input.file) as infile:
        #             kwargs['input'] = infile.read()
        #             #kwargs['test'] = form.test.interface
        #             #kwargs['test'].content = infile.readlines()
        # gather specific to the type (i.e. aws lambda)
        return getattr(self, 'gather_' + self.faas)(*args, **kwargs)

    def finish(self, context, result):
        """
        After a polyform is completed.
        """
        print("==> Starting DEX Finish")
        return getattr(self, 'finish_' + self.faas)(context, result)

# pylint: disable=invalid-name
class aws_lambda_polyform(PolyformDecorator):
    """
    For decorating AWS Lambda function calls.
    """
    def __init__(self, *args, **kwargs):
        kwargs['faas'] = 'lambda'
        super().__init__(*args, **kwargs)

    def gather_lambda(self, event, aws_context, **_kwargs):
        """Gather data expectations prior to running"""
        mylocals = Dict(
            context=dict(
                interface=dict(
                    event=event,
                    input={},
                    output={},
                    biome=dict(aws=aws_context)
                )
            ),
            dims=self.dims
        )

        if not self._interface or not self._interface.get('Input'):
            print("==> No interface.Input definition, not processing input data")
        else:
            body = event.get('parsed_body')
            print(body)
            if not body:
                body = event.get('body')
                print(body)
            mylocals.context.interface.input = gql_validate.validate(
                self._interface,
                'Input',
                body
            )

        # should check headers and give better errors, but assume its json
        return dex_intersect(self._cfg, self._form.expect, mylocals=mylocals)

    def finish_lambda(self, context, result):
        """Finish after running"""

        context.result = result
        if self._form.finish:
            context.interface.output = Dict()

            # do this explicitly to avoid it re-indexing Dict()
            mylocals = Dict(dims='', context='')
            mylocals.dims = self.dims
            mylocals.context = context

            context = dex_intersect(self._cfg, self._form.finish, mylocals=mylocals)
        else:
            context.interface.output = result

        if not self._interface or not self._interface.get('Output'):
            print("==> No interface.Output definition, not processing output data:")
            if context.interface.output:
                print("{}".format(context.interface.output))
            return {}
        return gql_validate.validate(self._interface, 'Output', context.interface.output)

def export(dict1):
    """
    Walk `dict1` which may be mixed dict()/Dict() and export any Dict()'s to dict()

    >>> export(Dict(first=1, second=dict(tres=Dict(nachos=2))))
    {'first': 1, 'second': {'tres': {'nachos': 2}}}
    """
    for key, value in dict1.items():
        if isinstance(value, Dict):
            dict1[key] = value.__export__()
        elif isinstance(value, dict):
            dict1[key] = export(value)
    return dict1

# pylint: disable=unused-argument
#def is_polyform(func):
#    """
#    for convenience, perpetuate a polyform object arg structure
#    """
