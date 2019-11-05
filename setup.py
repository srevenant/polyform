#!/usr/bin/env python3

from distutils.core import setup
import setuptools

setup(
    name='polyform',
    version='0.4.0',
    packages=[
      'polyform',
      'polyform.cli',
      'polyform.dev',
      'polyform.gql',
      'polyform.provider.aws',
      'polyform.sls',
      'polyform.util',
    ],
    license='None',
    long_description=open('README.md').read(),
    author='Brandon Gillespie',
    install_requires=[
      'dictlib',
      'pyyaml>=5',
      'pylint',
      'pyjwt',
      'boto3', # can move this to a plugin in the future
      'graphene>=2,<3'
    ],
    entry_points = {
      'console_scripts': [
        'poly=polyform.cli:entrypoint',
      ]
    },
)
