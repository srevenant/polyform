#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:

"""
Copyright 2019 Brandon Gillespie; All rights reserved.

We aren't doing full GraphQL, but we are trying for "close"

This is a fugly hack for the time being, until I have time to better understand
the python/graphql library
"""

import graphql
from graphql.language.ast import ObjectTypeDefinitionNode, NonNullTypeNode
# pylint: disable=unused-import
from graphql.error.syntax_error import GraphQLSyntaxError
from dictlib import Dict

# pylint: disable=line-too-long
def interface(indata):
    """
    >>> interface('''
    ... type NestedValue {
    ...     balance: Int!
    ... }
    ... type Input {
    ...     city: String!
    ...     state: String!
    ...     year: Int
    ...     moar: NestedValue!
    ... }
    ... type Output {
    ...     score: Float
    ... }
    ... ''')
    {'ast': {}, 'val': {'types': {'NestedValue': {'balance': {'nullok': False, 'type': 'Int'}}, 'Input': {'city': {'nullok': False, 'type': 'String'}, 'state': {'nullok': False, 'type': 'String'}, 'year': {'nullok': True, 'type': 'Int'}, 'moar': {'nullok': False, 'type': 'NestedValue'}}, 'Output': {'score': {'nullok': True, 'type': 'Float'}}}, 'ops': {}}}
    """
    if not indata:
        return []
    parsed = graphql.parse(indata)
    out = Dict(
        types={},
        ops={}
    )
    #for doc in graphql.parse(indata).definintions:
    for doc in parsed.definitions:
        if isinstance(doc, ObjectTypeDefinitionNode):
            fields = Dict()
            for field in doc.fields:
                newfield = Dict(nullok=True)
                ftype = field.type
                if isinstance(ftype, NonNullTypeNode):
                    newfield.nullok = False
                    ftype = ftype.type
                newfield.type = ftype.name.value
                fields[field.name.value] = newfield
            out.types[doc.name.value] = fields
        # elif isinstance(doc, OperationDefinition):
            # out.ops[doc.name.value] = doc
#             for oper in doc.
#
# OperationDefinition(
#   operation='query',
#   name=Name(value='OIScore'),
#   variable_definitions=[
#     VariableDefinition(
#       variable=Variable(name=Name(value='about')),
#       type=NonNullType(type=NamedType(name=Name(value='Input'))),
#       default_value=None
#     )
#   ],
#   directives=[],
#   selection_set=SelectionSet(
#     selections=[
#       Field(
#         alias=None, name=Name(value='score'),
#         arguments=[Argument(name=Name(value='about'),
#         value=Variable(name=Name(value='about')))],
#         directives=[],
#         selection_set=SelectionSet(
#           selections=[
#             Field(
#               alias=None,
#               name=Name(value='result'),
#               arguments=[],
#               directives=[],
#               selection_set=None)
#           ]
#         )
#       )
#     ]
#   )
#)
        else:
            raise AttributeError("Unrecognized gql type: '{}'".format(doc))
    return Dict(ast={}, val=out)
