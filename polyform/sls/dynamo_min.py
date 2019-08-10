#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Lambda Dynamo Min - running dynamo db for backend things -- minimal
'in serverless' version.
"""

#import boto3
from .boto3_min import Boto3Min

# pylint: disable=too-few-public-methods
class DynamoMin(Boto3Min):
    """Dynamo Wrapper for within a container"""
    table = ''

    def __init__(self, **config):
        super().__init__(resource='dynamodb', **config)
        self.table = config['schema']['TableName']

    def get(self, **key):
        """
        get item from a table using given key
        """
        return self.client.Table(self.table).get_item(Key=key).get('Item')

    def put(self, item):
        """
        put an item into a table
        """
        return self.client.Table(self.table).put_item(Item=item)
