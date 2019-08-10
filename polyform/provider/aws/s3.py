#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Lambda S3 - running s3 db for backend things.  See also S3Min in SLS
"""

# pylint: disable=relative-beyond-top-level
#import os
#import sys
#import time
#import io
#import base64
#import zlib
#from datetime import datetime
#from decimal import Decimal
#from uuid import uuid4
#import jwt
#import dictlib
from ...sls.s3_min import S3Min

class S3(S3Min):
    """
    S3 class, wrapping of s3 functionality for simpler use outside of
    serverless functions.
    """
    def wait(self, event, obj):
        """
        Run a obj call that can support a waiter, and wrap it with a waiter
        """
        return obj.meta.client.get_waiter(event).wait(Bucket=self.bucket)

    def create_bucket(self, **_kwargs):
        """
        Create an s3 bucket
        """
        bucket_name = self.bucket

        # probably not the best idea
        # pylint: disable=protected-access
        region_name = self.client.meta.client._client_config.region_name

        print("Create bucket " + bucket_name)
        # it throws an error on failure
        self.client.create_bucket(
            ACL='private', # |'public-read'|'public-read-write'|'authenticated-read',
            Bucket=bucket_name,
            CreateBucketConfiguration=dict(
                LocationConstraint=region_name
            ),
            ObjectLockEnabledForBucket=False
        )
        # self.wait('bucket_exists', self.client.create_bucket(**bucket_schema))

    def drop_bucket(self):
        """
        Drop a s3 bucket
        """
        self.wait('bucket_not_exists', self.client.delete_bucket(self.bucket))

    def delete(self, keyid):
        """
        delete an item from a bucket
        """
#
# # ################################################################################
# def provision(configs):
#     """
#     Provisioning backend elements for a lambda service.  This is
#     only needed to create the foundaional bits.
#     """
#     for name in configs:
#         config = configs[name]
#         if config['driver'] != 'aws-s3':
#             continue
#         s3c = S3(**config)
#         print('create s3db bucket=' + s3c.bucket + '...')
#         aws_trap('Bucket', s3c.create_bucket, **config['schema'])
#
# def deprovision(config):
#     """
#     Deprovisioning backend elements for a lambda service.  This is
#     only needed to create the foundaional bits.
#     """
#     for name in config:
#         config = config[name]
#         dyn = S3(config)
#         print('drop s3db bucket=' + dyn.bucket + '...')
#         aws_trap('Table', dyn.drop_bucket)
# #
# # def get_s2_config(config, role):
# #     """
# #     search db configs for one with named role
# #     """
# #     for name in config:
# #         conf = config[name]
#         if conf.get('role') == role:
#             conf['role'] = name
#             return dictlib.Dict(conf)
#     return None
#
# def cmd_node_push(config, duid, fpath):
#     """
#     Update a record, contents stored at element in dictionary contents
#     """
#     client = S3(**get_s3_config(config, 'BackingData'))
#     with open(fpath, 'rb') as infile:
#         # data = base64.b64encode(zlib.compress(infile.read())).decode()
#         client.put(key=duid, file=infile)
#
# def cmd_node_pull(config, duid):
#     """
#     Pull a record
#     """
#     # TODO: should wrap this with a driver check, to handle various
#     client = S3(**get_s3_config(config, 'BackingData'))
#     rfd = client.get(key=duid)
#     while sys.stdout.buffer.write(rfd.read(amt=4096)):
#         pass
#    dyn = S3(get_s3_config(config, 'BackingData'))
#    item = dyn.get(id=duid)
#    print(zlib.decompress(base64.b64decode(item[element])).decode())

# def aws_trap(label, func, *args, **kwargs):
#     """
#     wrap a function call and catch common errors from boto3
#     """
#     try:
#         func(*args, **kwargs)
#     except Exception as err: # pylint: disable=broad-except
#         errname = err.__class__.__name__ # boto3 error handling is painful
#         if errname == 'ResourceNotFoundException':
#             print("{} doesn't exist".format(label))
#         elif errname == 'ResourceInUseException':
#             print(err)
#         elif errname == 'AttributeError':
#             print("{} is still deleting".format(label))
#         else:
#             print(errname)
#             raise
#
# AUTH_APIKEY_EXPIRES = 31536000 # 1 year
# def key_auth_skeleton():
#     """
#     Generate a new/skeleton object (AuthAPI)
#     """
#     return {
#         "id": str(uuid4()),
#         "type": "apikey",
#         "expires_at": Decimal(int(time.time() + AUTH_APIKEY_EXPIRES)),
#         "secret": base64.b64encode(os.urandom(64)).decode()
#     }
