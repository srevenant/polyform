#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
# pylint: disable=import-error

"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Lambda Arc - A thin version of Reflex Arc for running within containers.

Primarily for proof-of-concept purposes.

see polyform.dex for more info.

This is the intersect/exection side of DEX
"""

import os
#import re
import sys
import json
#import base64
#import zlib
import pickle
import tempfile
import traceback
from io import StringIO
#from xgboost import XGBClassifier
import jwt
import datacleaner
import pandas
import dictlib
from dictlib import Dict
from .dynamo_min import DynamoMin
from .s3_min import S3Min

DEBUG = not not os.environ.get('DEBUG') # pylint: disable=unneeded-not

# setting message this way isn't translating into __repr__ properly, need
# to spend a few mins and figure out how to propagate the message properly
class DEXError(Exception):
    """
    Throw an error, but give the bits that compose the error, this will
    assemble it as a message
    """
    message = None
    # pylint: disable=too-many-arguments
    def __init__(self, nbr=0, expr='', msg='', status='', error=None):
        super().__init__()
        self.message = "DEX {status} nbr={nbr} expr={expr}".format(
            status=status,
            nbr=nbr,
            expr=json.dumps(expr),
        )
        if msg:
            self.message += ' msg=' + json.dumps(msg)
        if error:
            self.message += ' error='
            self.message += json.dumps(error.__class__.__name__ + ": " + str(error))

# TODO: remove hardwired name
BDATA = S3Min(schema=dict(Bucket='4E5DDD33F59A4D4086756BA77698213D'))
def dex_eval_locals(defaults):
    """
    create our eval locals
    """
    mylocals = dict() # locals() # pylint: disable=redefined-builtin
    def dex_assign(value, data, key):
        if isinstance(key, list):
            dictlib._dug(data, value, *key) # pylint: disable=protected-access
        else:
            data[key] = value
        return value
    def dex_pull(duid, typedef=None):
        ## TEMPORARY
        print("PULL({})".format(duid))
        if typedef == 'pickle>>*':
            with tempfile.TemporaryFile() as wfd:
                rfd = BDATA.get(key=duid)
                while wfd.write(rfd.read(amt=4096)):
                    pass
                wfd.seek(0)
                return pickle.load(wfd)
        if typedef == 'json':
            return json.load(BDATA.get(key=duid))
        if typedef == 'csv>>dataframe':
            return pandas.read_csv(BDATA.get(key=duid))
        if typedef is None:
            return BDATA.get(key=duid).read()
        raise Exception("pull(): Unrecognized typedef: " + typedef)
    def dex_push(data, duid, typedef=None):
        if isinstance(data, Dict):
            data = data.__export__()
        print("PUSH({})".format(duid))
        if typedef == '*>>pickle':
            with tempfile.TemporaryFile() as xfd:
                pickle.dump(data, xfd)
                xfd.seek(0)
                return BDATA.put(key=duid, file=xfd)
        if typedef is None:
            return BDATA.put(key=duid, body=data)
        raise Exception("push(): Unrecognized typedef: " + typedef)
    def dex_follow(node, key):
        raise Exception("Not yet implemented")
    def dex_in_range(data, start, end):
        return start <= data <= end
    # def dex_serialize(data):
    #     typedef = type(data)
    #     print("SERIALIZE({})".format(typedef))
    #     if isinstance(data, XGBClassifier):
    #         typedef = b'pickle00'
    #         return base64.b64encode(typedef + pickle.dumps(data))
    #         tmpfile = tempfile.mkstemp()
    #
    #         # data.to_parquet(tmpfile)
    #         # with open(tmpfile, 'rb') as outfile:
    #         #     buffer = outfile.read()
    #         # serialized = typedef + base64.b64encode(buffer)
    #         # os.unlink(tmpfile)
    #         # return serialized
    #     raise Exception("serialize(): Unrecognized typedef: " + typedef)
    # def dex_deserialize(data, type):
    #     typedef = data[0:8]
    #     print("DESERIALIZE({})".format(typedef))
    #     data = data[8:]
    #     if typedef == 'xgbclass':
    #         return pickle.loads(base64.b64decode(data))
    #         # tmpfile = tempfile.mkstemp()
    #         # with open(tmpfile, 'wb') as outfile:
    #         #     outfile.write(base64.b64decode(tmpfile))
    #         # model = XFGClassifier.from_parquet(tmpfile)
    #         # os.unlink(tmpfile)
    #         # return model
    #     raise Exception("serialize(): Unrecognized typedef: " + typedef)
    def dex_convert(data, typedef, *args, **kwargs):
        if typedef == "*>>json":
            return json.dumps(data)
        if typedef == "json>>*":
            return json.loads(data)
        if typedef == "csv>>dataframe":
            return pandas.read_csv(StringIO(data))
        if typedef == "dataframe>>csv":
            return pandas.DataFrame.to_csv(data)
        if typedef == "dataframe>>dict":
            return pandas.DataFrame.to_dict(data)
        if typedef == "dataframe>>json":
            return data.to_json()
        if typedef == "dict-row>>dataframe":
#            out = {key: {"0": value} for key, value in data.items()}
#            return pandas.read_json(json.dumps(out))
            out = {key: [value] for key, value in data.items()}
            return pandas.DataFrame.from_dict(out, orient='columns') # , orient='index')
        # if typedef == "stored>>csv>>dataframe":
        #     return pandas.read_csv(StringIO(zlib.decompress(base64.b64decode(data)).decode()))
        # if typedef == "*>>base64":
        #     return base64.b64encode(data).decode() # pull off byte/utf
        # if typedef == "base64>>*":
        #     return base64.b64decode(data)
        # if typedef == "b64gz>>txt":
        #     return base64.b64encode(zlib.compress(data).encode()).decode()
        # if typedef == "txt>>b64gz":
        #     return zlib.decompress(base64.b64decode(data)).decode()
        raise Exception("convert(): Unrecognized typedef: " + typedef)
    def dex_inspect(data, label=None):
        if label:
            sys.stdout.write("{}: ".format(label))
        sys.stdout.write("{}\n".format(data))
        return data

    if defaults:
        mylocals.update(defaults)
    mylocals.update(dict(
        assign=dex_assign,
        pull=dex_pull,
        push=dex_push,
        follow=dex_follow,
        in_range=dex_in_range,
        #serialize=dex_serialize,
        #deserialize=dex_deserialize,
        inspect=dex_inspect,
        autoclean=datacleaner.autoclean,
        convert=dex_convert
    ))
    return mylocals

def dex_intersect(polyform, dex_exprs, mylocals=None):
    """
    evaluate an intersection's data expectations
    """
    if not mylocals:
        raise AttributeError("Missing mylocals={}")
    # mylocals.update(Dict(
    #     interface=Dict(),
    #     Output=Dict(),
    #     Result=Dict()
    # ))
    mylocals['context'].update(
        creator=None,
        invoker=None,
        requestor=None,
        appexdev=None,
        polydev=Dict(id=polyform.meta.owner)
    )
    mylocals = dex_eval_locals(mylocals)

    try:
        row = 0
        for expr in dex_exprs:
            if DEBUG:
                print(">>> {}".format(mylocals['context']))
                print(">>> {}".format(expr))
            row += 1
            # lift context up into primary locals
            mylocals.update(mylocals['context'])
            result = eval(expr, mylocals) # pylint: disable=eval-used

            # why does pandas.DataFrame think it's special, gah
            if not isinstance(result, pandas.DataFrame) and not result:
                raise DEXError(nbr=row, expr=expr, status="not-true",
                               msg="Expression did not result in a true value")
    except DEXError:
        raise
    except Exception as err: # pylint: disable=broad-except
        if DEBUG:
            traceback.print_exc()
        raise DEXError(nbr=row, expr=expr, status="error", error=err)
    return mylocals['context']

# Auth table:
#   tokenKey
#   tokenSecret
#   tokenExpires

def lambda_proxy_auth(event, _context):
    """
    check if an incoming event has the proper authentication header,
    and if its good
    """
    auth = event["headers"].get("Authorization") # or event["headers"].get("authorization")
    auth = matching_begin("Bearer ", auth)
    if not auth:
        return False # response(event, "Deny")
    if verify_access_token(auth):
        return True # response(event, "Allow")
    return False # response(event, "Deny")

# case SENSITIVE
def matching_begin(begin, arg):
    """match beginning of a string and return the unmatched part"""
    slen = len(begin)
    if arg[0:slen] == begin:
        return arg[slen:]
    return False

class AuthFailed(Exception):
    """auth failed"""

def verify_access_token(token):
    """verify if an access token meets our criteria"""
    try:
        claims = jwt.decode(token, verify=False)
        # sub: cas1:ID
        uid = matching_begin("cas1:", claims['sub'])
        if not uid:
            raise AuthFailed("Auth Error: UID doesn't exist?")
        ident = DynamoMin(schema={"TableName": "AuthApikeys"}).get(id=uid)
        if not ident:
            raise AuthFailed("Auth Error: cannot get identity table")
        # TODO: add verification for 'aud'
        return jwt.decode(token, ident['secret'], audience=claims['aud']) # , algorithm='HS256'
    except (jwt.exceptions.DecodeError, jwt.exceptions.ExpiredSignatureError) as err:
       # print("Auth Error: " + str(err))
        raise AuthFailed("Auth Error: " + str(err))
    except: # pylint: disable=bare-except
        # watch logs, trim this over time
        traceback.print_exc()
        raise AuthFailed("Auth Error: " + str(err))
        return False

#def response(_event, effect):
#    """Respond to an auth -- now a temporary holder"""
#    return effect == "Allow"
