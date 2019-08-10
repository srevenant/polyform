#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Lambda Dynamo - running dynamo db for backend things.  See also DynamoMin in SLS
"""

# pylint: disable=relative-beyond-top-level
#import os
#import time
#import base64
#import zlib
#from datetime import datetime
#from decimal import Decimal
#from uuid import uuid4
#import jwt
#import dictlib
#from . import aws_trap
#from ...config import get_resource_config
from ...sls.dynamo_min import DynamoMin

class Dynamo(DynamoMin):
    """
    Dynamo class, wrapping of dynamo functionality for simpler use outside of
    serverless functions.
    """
    def wait(self, event, table_obj):
        """
        Run a table call that can support a waiter, and wrap it with a waiter
        """
        return table_obj.meta.client.get_waiter(event).wait(TableName=self.table)

    def create_table(self, **table_schema):
        """
        Create a dynamo DB table
        """
        # reference AuthX backend 'Factors' table
        #   id=UUID
        #   type=string ENUM(unknown, password, federated, valtok, apikey, proxy)
        #   expires_at=int
        #   secret=string
        #     could add: name, value, details, hash
        self.wait('table_exists', self.client.create_table(**table_schema))

    def drop_table(self):
        """
        Drop a dynamo DB table
        """
        table = self.client.Table(self.table)
        self.wait('table_not_exists', table.delete())

    def scan(self):
        """
        Scan a table for all keys.  not optimal, so use sparingly
        """
        return self.client.Table(self.table).scan()

    def delete(self, keyid):
        """
        delete an item from a table
        """
        return self.client.Table(self.table).delete_item(Key={'id': keyid})

    def update(self, item):
        """
        update an item in a table
        """
        return self.client.Table(self.table).update_item(Item=item)
