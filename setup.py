#!/usr/bin/env python3

from distutils.core import setup
import setuptools

setup(
    name='polyform',
    version='0.2.6',
    packages=[
      'polyform',
      'polyform.cli',
      'polyform.dev',
      'polyform.gql',
      'polyform.provider',
      'polyform.sls',
      'polyform.util',
    ],
    license='None',
    long_description=open('README.md').read(),
    author='Brandon Gillespie',
    install_requires=[
      'dictlib',
      'pyyaml',
      'pylint',
      'pyjwt',
      'boto3', # can move this to a plugin in the future
      'graphene>=2'
    ],
    entry_points = {
      'console_scripts': [
        'poly=polyform.cli:entrypoint',
      ]
    },
)
