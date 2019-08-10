#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Lambda Dynamo - running dynamo db for backend things.  See also DynamoMin in SLS
"""

# import os
# import time
import base64
import zlib
# from datetime import datetime
# from decimal import Decimal
# from uuid import uuid4
# import jwt
# import dictlib
from .. import auth
from ..config import get_resource_config
from ..provider.aws import aws_trap
from ..provider.aws.dynamo import Dynamo

def cmd_apikey_new(config):
    """
    Command for a new APIkey
    """
    dyn = Dynamo(**get_resource_config(config, 'APIAuthentication'))
    def inner():
        skel = auth.key_auth_skeleton()
        dyn.put(skel)
        print(auth.format_apikey(skel))
    aws_trap("Cannot create apikey (is table provisioned?), APIkey Table", inner)

def cmd_apikey_ls(config):
    """
    Command for listing APIkeys
    """
    dyn = Dynamo(**get_resource_config(config, 'APIAuthentication'))
    def inner():
        for item in dyn.scan()['Items']:
            print(auth.format_apikey(item))
    aws_trap("Cannot list apikeys (is table provisioned?), APIkey Table", inner)

def cmd_apikey_del(config, *keyids):
    """
    Command for deleting APIkeys
    """
    dyn = Dynamo(**get_resource_config(config, 'APIAuthentication'))
    def inner():
        for key in keyids:
            result = dyn.delete(key)
            if result.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200:
                print("{} => OK".format(key))
            else:
                print("{} => {}".format(key, result))
    aws_trap("Cannot create apikey (is table provisioned?), APIkey Table", inner)

def cmd_provision(datastores):
    """
    Command for provisioning backend elements for a lambda service.  This is
    only needed to create the foundaional bits.
    """
    for name in datastores:
        config = datastores[name]
        if config.get('driver') != 'aws-dynamo':
            continue
        dyn = Dynamo(**config)
        print('create dynamodb table=' + dyn.table + '...')
        aws_trap('Table', dyn.create_table, **config['schema'])

def cmd_deprovision(datastores):
    """
    Command for deprovisioning backend elements for a lambda service.  This is
    only needed to create the foundaional bits.
    """
    for name in datastores:
        config = datastores[name]
        if config.get('driver') != 'aws-dynamo':
            continue
        dyn = Dynamo(**config)
        print('drop dynamodb table=' + dyn.table + '...')
        aws_trap('Table', dyn.drop_table)

# def cmd_node_push(config, duid, element, fpath):
#     """
#     Update a record, contents stored at element in dictionary contents
#     """
#     dyn = Dynamo(**get_resource_config(config, 'BackingData'))
#     with open(fpath, 'rb') as infile:
#         data = base64.b64encode(zlib.compress(infile.read())).decode()
# #        print(data)
# #        print(zlib.decompress(base64.b64decode(data)).decode())
#     return dyn.put({
#         "id": duid,
#         "lane": "prd",
#         element: data
#     })
#
# def cmd_node_pull(config, duid, element):
#     """
#     Pull a node from the data universe
#     -- but not really, just from our temp datastore
#     """
#     dyn = Dynamo(**get_resource_config(config, 'BackingData'))
#     item = dyn.get(id=duid)
#     print(zlib.decompress(base64.b64decode(item[element])).decode())
