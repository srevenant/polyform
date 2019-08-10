#!/usr/bin/env python3

from distutils.core import setup
import setuptools

setup(
    name='polyform',
    version='0.2.5',
    packages=['polyform', 'polyform.util', 'polyform.dev', 'polyform.aws', 'polyform.sls'],
    license='None',
    long_description=open('README.md').read(),
    author='Brandon Gillespie',
    install_requires=[
      'dictlib',
      'pyyaml',
      'pylint',
      'pyjwt',
      'boto3', # can move this to a plugin in the future
      'graphql'
    ],
    entry_points = {
      'console_scripts': [
        'poly=polyform.cli:entrypoint',
      ]
    },
)
