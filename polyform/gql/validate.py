#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:

"""
Copyright 2019 Brandon Gillespie; All rights reserved.

We aren't doing full GraphQL, but we are trying for "close"

This is a fugly hack for the time being, until I have time to better understand
the python/graphql library
"""

class DataValidationError(Exception):
    """Raise a Data Validation error"""

def validate(schema, typedef, data):
    """
    Validate data against a schema
    """
#    print(">>> validate({},{},{})".format(schema, typedef, "{data}"))
    return CheckTypes(schema).validate(typedef, data, ref="Input")

# pylint: disable=no-self-use
class CheckTypes():
    """Used as part of data validation"""
    depth = 0
    schema = {key: {'call': 'check_' + key} for key in ('Int', 'Float', 'String', 'Boolean', 'ID')}

    def __init__(self, schema):
        self.schema = self.schema.copy()
        for key in schema:
            self.schema[key] = {'fields': schema[key]}

    def validate(self, typedef, data, ref=None):
        """Entry point"""
#        print(">>> CheckTypes.validate({},{})".format(typedef, data))
        #print("??? TYPEDEF={}".format(typedef))
        #print("... {}".format(self.schema[typedef]))
        #print("---{}".format(self.schema[typedef]))
        try:
            fields = self.schema[typedef].get('fields')
        except KeyError as error:
            msg = "specified data type `{}` is not valid for key `{}`".format(typedef, ref)
            raise DataValidationError(msg)
        if not fields:
            call = self.schema[typedef].get('call')
            if call:
                #print("CALL >> {}({},{},{})".format(call, ref, typedef, data))
                return getattr(self, call)(ref, typedef, data)
            #print("HURM")

        new = dict()
        remainder = data.copy()
        for key in fields:
#            print("FIELDS={}".format(fields))
            # each col defined on type
#            print("key={}.{}".format(typedef, key))
            spec = fields[key]
            val = data.get(key)
#            print("VAL?=>{}".format(val))
            if val is None:
                if spec['nullok']:
#                    #print("Null OK for {}".format(key))
                    continue
                raise DataValidationError("key `{}` missing or not matching type, from payload (type=`{}`)".format(key, typedef))

            call = spec.get('call')
            if call:
                raise DataValidationError("Unexpected call on field data type")
            typedef = spec.get('type')
            if typedef:
                new[key] = self.validate(typedef, data[key], ref=key)
            del remainder[key]
        if remainder:
            # TODO: Check nullok
            raise DataValidationError("Unexpected element: {}".format(", ".join(remainder.keys())))
        return new

    # pylint: disable=invalid-name
    def check_ISO8601Date(self, ref, key, value):
        """Check an ISO8601 Date -- need to implemet still"""
        return self.check_String(ref, key, value)

    # pylint: disable=invalid-name
    def check_Int(self, ref, key, value):
        """Check as an integer"""
        if isinstance(value, int):
            return value
        raise DataValidationError(badtype(ref, 'int', value))

    # pylint: disable=invalid-name
    def check_Float(self, ref, key, value):
        """Check as a float or integer, return float"""
        if isinstance(value, float):
            return value
        if isinstance(value, int):
            return float(value)
        raise DataValidationError(badtype(ref, 'float', value))

    # pylint: disable=invalid-name
    def check_String(self, ref, key, value):
        """Check as a string"""
        if isinstance(value, str):
            return value
        raise DataValidationError(badtype(ref, 'str', value))

    # pylint: disable=invalid-name
    def check_Boolean(self, ref, key, value):
        """Check as true or false"""
        if isinstance(value, bool):
            return value
        raise DataValidationError(badtype(ref, 'bool', value))

    # pylint: disable=invalid-name
    def check_ID(self, ref, key, value):
        """Check as an ID (string)"""
        return self.check_String(ref, key, value)

    #def __getattr_():
    #    pass

def badtype(key, wanted_type, received):
    """format a standard error message"""
    # pylint: disable=line-too-long
    return "Data element `{}` does not match schema type. It is type=`{}`, where we want type=`{}`" \
        .format(key, type(received).__name__, wanted_type)

#
# import parse
# parsed = parse.interface("""
#     type Input {
#         city: String!
#         loan_amount: Int!
#         balance: Float!
#     }
# """)
# schema = parsed['val']['types']
#
# result = validate(schema, 'Input', dict(
#   city="moop",
#   loan_amount=200,
#   balance=1,
#   mo_balance="foo"
# ))
#
# print(result)
