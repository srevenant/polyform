#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Lambda S3 Min - running dynamo db for backend things -- minimal
'in serverless' version.
"""

#import os
#import boto3
from .boto3_min import Boto3Min
#from ..provider.aws import fix_lambci_env

# pylint: disable=too-few-public-methods
class S3Min(Boto3Min):
    """S3 Wrapper for within a container"""
    bucket = ''

    def __init__(self, **config):
        super().__init__(resource='s3', **config)
        self.bucket = config['schema']['Bucket'].lower()

    def get(self, key=''):
        """
        get item from a table using given key
        """
        return self.client.Object(self.bucket, key).get()['Body']

    def put(self, key='', body='', file=None):
        """
        put up an item
        """
        if file:
            return self.client.Object(self.bucket, key).put(Body=file)
        return self.client.Object(self.bucket, key).put(Body=body)
