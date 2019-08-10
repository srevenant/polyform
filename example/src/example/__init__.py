#!/usr/bin/env python3
#$#HEADER-START
# vim:set expandtab ts=4 sw=4 ai ft=python:
#$#HEADER-END

# pylint: disable=unused-argument
"""
Module Description Here
"""

import sys
import os
import polyform
from polyform.sls.decorators import aws_lambda_polyform, Result

@aws_lambda_polyform
def test(poly, context=None, dims=None): # pylint: disable=unused-argument
    """doc"""
    print("test")
    return Result(value="returned value")

@aws_lambda_polyform
def legacy_training(poly, context=None, dims=None): # pylint: disable=unused-argument
    """function doc -- pair up or blend w/Polyform.yml doc?"""

    # do training with context["csv"],
    # which is already processed/validated from poly.input.event.csv
    # then return the model in the result, which is stored as part of our finish frame
    return Result(model="")

@aws_lambda_polyform
def better_training(poly, context=None, dims=None): # pylint: disable=unused-argument
    """function doc -- pair up or blend w/Polyform.yml doc?"""

    # in this one our context includes the data gathered from the universe, instead
    # of explicitly sent via CSV
    return Result(model="")

@aws_lambda_polyform
def ask_for_thing(poly, context=None, dims=None): # pylint: disable=unused-argument
    """function doc -- pair up or blend w/Polyform.yml doc?"""
    return Result(score=0.9555,
                  report=dict({
                      "status": "YELLOW",
                      "reason": "Asked for too much",
                      "explanation": "Recommended range is 1200-1500"
                  }))

@aws_lambda_polyform
def is_good_fit(poly, context=None, dims=None):
    """doc"""
    return Result()
