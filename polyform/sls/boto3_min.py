#tom !/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Lambda Dynamo Min - running dynamo db for backend things -- minimal
'in serverless' version.
"""

import os
import boto3

# pylint: disable=too-few-public-methods
class Boto3Min():
    """Dynamo Wrapper for within a container"""
    client = None
    config = None

    def __init__(self, resource=None, **config):
        if not resource:
            raise AttributeError("Missing resource= for Boto3Min().__init__()")

        prep_aws_environ() # adjusting lambci things
        self.config = config
        # TODO: bring in global config <is self avail with incept?>
        self.client = boto3.resource(resource)

# lambci injects vars, even if I don't want to use them
def prep_aws_environ():
    """verify and adjust our environment so it works for a signin"""
    if os.path.exists('/.aws/credentials'):
        print("using /.aws/credentials")
        os.environ['AWS_SHARED_CREDENTIALS_FILE'] = '/.aws/credentials'
    for key in os.environ:
        if key[:3] == 'AWS':
            val = os.environ[key]
            if val in ('SOME_ACCESS_KEY_ID', 'SOME_SECRET_ACCESS_KEY'):
                del os.environ[key]
#    for key in ('AWS_PROFILE',):
#        if key not in os.environ:
#            raise AttributeError(key + " is not set in environment")
