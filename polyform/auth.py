#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Lambda Dynamo - running dynamo db for backend things.  See also DynamoMin in SLS
"""

import os
import time
import base64
#import zlib
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
import jwt
#import dictlib
#from ..sls.lambda_dynamo_min import DynamoMin

AUTH_APIKEY_EXPIRES = 31536000 # 1 year - ugly magic var stored inline

def format_apikey(item):
    """
    standard APIkey format output
    """
    return "{}:\n  key = {}\n  expires = {}".format(
        item['id'],
        jwt.encode({
            'sub': 'cas1:' + item['id'],
            'exp': int(item['expires_at']),
            'aud': 'caa1:acc:' # TODO: domain for acc token
        }, str(item['secret'])).decode(),
        datetime.fromtimestamp(item['expires_at'])
    )

def key_auth_skeleton():
    """
    Generate a new/skeleton object (AuthAPI)
    """
    return {
        "id": str(uuid4()),
        "type": "apikey",
        "expires_at": Decimal(int(time.time() + AUTH_APIKEY_EXPIRES)),
        "secret": base64.b64encode(os.urandom(64)).decode()
    }
