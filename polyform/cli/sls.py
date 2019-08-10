#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Lambda - provision
"""

import os
import sys
import json
import boto3
import base64
from dictlib import Dict
from ..provider.aws import aws_trap
from ..provider.aws.s3 import S3
from ..sls.boto3_min import prep_aws_environ

POLYROLE = 'PolyformLambdaRole'

def get_func(sls, target):
    try:
        return sls.get_function(FunctionName=target)
    except Exception as err: # pylint: disable=broad-except
        errname = err.__class__.__name__ # boto3 error handling is painful
        if errname == 'ResourceNotFoundException':
            return None
        else:
            raise

def get_build(form_name, fname):
    path = os.path.join('_build', form_name, fname)
    if not os.path.exists(path):
        sys.exit("Cannot find `{}`".format(path))
    print("reading {}".format(path))
    with open(path, 'rb') as infile:
        return infile.read()

def get_s3_bucket(polyform, form_name, handler):
    bucket = polyform.forms[form_name].deploy.get('aws', {}).get('bucket')
    if not bucket:
        print("Deriving bucket name (set deploy.aws.bucket to remove this warning)")
        domain = polyform.meta.domain.replace('.', '-').lower()
        name = polyform.meta.name.replace('.', '-').replace('_', '-')
        bucket = '{}-{}-{}-{}'.format(
            domain, name, form_name,
            base64.b64encode(handler.encode()).decode()
        )
        bucket = bucket.replace('=', '').lower()

    return bucket

def cmd_deploy(polyform, target, handler):
    """
    deploy a lambda function
    """
    name = "polyform-{}-{}".format(polyform.meta.name, target)
    print(name)
    iam = boto3.client('iam')
    sls = boto3.client('lambda')
    func = get_func(sls, name) # already defined?
    if not func:
        # define it
        pass
#        sls.create_func(

    bucket = get_s3_bucket(polyform, target, handler)
    form = polyform.forms[target]
    deploy = Dict(form.deploy['aws'])
    timeout = deploy.get('timeout', 60)
    if timeout > 300:
        sys.exit("Timeout greater than 300 is disallowed")
    env = deploy.get('env', {})
    if isinstance(env, str):
        env = [env]
    if env is None:
        env = {}
    elif isinstance(env, list):
        env = {}
        for line in deploy.get('env'):
            if not line or not "=" in line:
                sys.exit("Invalid deploy.env value for form, not KEY=VALUE")
            name, value = line.split("=", 1)
            if value[0] == '"':
                value = json.loads(value)
            env[name] = value
        print(env)
    elif not isinstance(env, dict):
        sys.exit("Invalid deploy.env for form, not dictionary or list of KEY=VALUE")

    code_data = get_build(target, 'func.latest.zip')
    libs_data = get_build(target, 'libs.latest.zip')
    role = iam.get_role(RoleName=POLYROLE)
    tags = deploy.get('tags', {})

    s3c = S3(schema=dict(Bucket=bucket))
    #print('create s3db bucket=' + s3c.bucket + '...')
    aws_trap('Bucket', s3c.create_bucket)

    print(polyform.meta.__dict__)
    layer = aws_trap("Function Libs", sls.publish_layer_version,
        LayerName=name + "-libs",
        Content=dict(
          S3Bucket=bucket,
          S3Key=name + "-libs",
          ZipFile=libs_data
        ),
        CompatibleRuntimes=[polyform.meta.language.lambci]
    )

    print(layer)
    return
    aws_trap("Function", sls.create_function,
        FunctionName=name,
        Runtime=polyform.meta.language.lambci,
        Role=role['Role']['Arn'],
        Handler=handler,
        Code=dict(ZipFile=code_data),
        Timeout=timeout,
        Environment=dict(Variables=env),
        Tags=tags
    )


def cmd_provision(_config):
    """
    Command for provisioning backend elements for a lambda service.
    """
    prep_aws_environ()
    #account_id = boto3.client('sts').get_caller_identity().get('Account')
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }]
    }

    iam = boto3.client('iam')
    aws_trap('Role', iam.create_role,
        RoleName=POLYROLE,
        AssumeRolePolicyDocument=json.dumps(policy),
    )

    sls = boto3.client('lambda')

def cmd_deprovision(datastores):
    """
    deprovisioning
    """
    iam = boto3.client('iam')
    aws_trap('Role', iam.delete_role, RoleName=POLYROLE)
