#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Lambda S3 - running s3 db for backend things.  See also S3Min in SLS
"""

#import os
import sys
#import time
#import io
#import base64
#import zlib
#from datetime import datetime
#from decimal import Decimal
#from uuid import uuid4
#import jwt
#import dictlib
from ..provider.aws import aws_trap
from ..provider.aws.s3 import S3
from ..config import get_resource_config
#from ..sls.s3_min import S3Min

################################################################################
def cmd_node_push(config, duid, fpath):
    """
    Update a record, contents stored at element in dictionary contents
    """
    client = S3(**get_resource_config(config, 'BackingData'))
    with open(fpath, 'rb') as infile:
        # data = base64.b64encode(zlib.compress(infile.read())).decode()
        client.put(key=duid, file=infile)

def cmd_node_pull(config, duid):
    """
    Pull a record
    """
    # TODO: should wrap this with a driver check, to handle various
    client = S3(**get_resource_config(config, 'BackingData'))
    rfd = client.get(key=duid)
    while sys.stdout.buffer.write(rfd.read(amt=4096)):
        pass
#    dyn = S3(get_resource_config(config, 'BackingData'))
#    item = dyn.get(id=duid)
#    print(zlib.decompress(base64.b64decode(item[element])).decode())

def cmd_provision(configs):
    """
    Command for provisioning backend elements for a lambda service.  This is
    only needed to create the foundaional bits.
    """
    for name in configs:
        config = configs[name]
        if config['driver'] != 'aws-s3':
            continue
        s3c = S3(**config)
        print('create s3db bucket=' + s3c.bucket + '...')
        aws_trap('Bucket', s3c.create_bucket, **config['schema'])

def cmd_deprovision(_config):
    """
    deprovision backend
    """
    for name in configs:
        config = configs[name]
        if config['driver'] != 'aws-s3':
            continue
        s3c = S3(**config)
        print('delete s3db bucket=' + s3c.bucket + '...')
        aws_trap('Bucket', s3c.delete_bucket, **config['schema'])
