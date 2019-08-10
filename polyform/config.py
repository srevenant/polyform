#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:

# pylint: disable=no-self-use,unused-argument,missing-docstring,protected-access,too-few-public-methods

"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Quick hack: Parsing of Polyform configurations, load and dump
"""

import os
import re
import json
import copy
from functools import singledispatch
import dictlib
from dictlib import Obj as Dict
import yaml
from .gql import parse as gql_parse
from .dex import dex_transpile
from .util.out import debug, notify, header, error, abort # pylint: disable=unused-import

def multiline_yaml(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, multiline_yaml)

# things always needed within a container
GLOBAL_PIP = [
    'boto3', # React Arc: AWS boto3 into dynamo
    'jwt', # React Arc: Handling authentication tokens
    'dictlib', # general polyform utility
    'datacleaner'
]

################################################################################
class Config():
    """
    Polyform.yml configuration object
    """
    polyform = None

    def _find_path(self, path=None):
        """
        Find the Polyform.yml config. We used to support more locations and names.
        """
        if not path:
            for base in ["."]:
                path = base + "/Polyform.yml"
                if os.path.exists(path):
                    return path
        return None

    def __init__(self, path=None, skeleton=False):
        spec = dict()
        if skeleton:
            spec = {}
        else:
            if not path:
                path = self._find_path(path)
            if not path:
                abort("Cannot find Polyform.yml")

            with open(path) as infile:
                try:
                    # CLoader faster, but is a difficult dependency
                    spec = yaml.full_load(infile)
                except Exception as err: # pylint: disable=broad-except
                    abort(err)

        # enforce structure around code testing
        # TODO: this is only for python at the moment; split this out so
        # pip always is run on GLOBAL_PIP, separate from whatever the language
        # of the form wants
        code_default = dict(type="codetest", dependencies={"add": GLOBAL_PIP + ["pylint"]})
        code_test = dictlib.dig_get(spec, "forms.codetest", None)
        if code_test:
            code_test = dictlib.union_setadd(code_test, code_default)
            dictlib.dug(spec, "forms.codetest", code_test)
        else:
            dictlib.dug(spec, "forms.codetest", code_default)

        # load up the polyform config
        self.polyform = Polyform(keyword="polyform", config=self)
        self.polyform._add_keys(spec)

        # finish
        self.polyform._finish()

def to_json(config_dict, **kwargs):
    """
    Output as JSON

    TODO: create test space with default polyform
    > self.to_json()
    1
    """
    if isinstance(config_dict, Config):
        config_dict = config_dict.polyform._export()
    kwargs['default'] = to_serializable
    return json.dumps(config_dict, **kwargs)

def to_yaml(config_dict, **kwargs):
    """
    Output as YAML
    """
#        kwargs['default'] = to_serializable
    # silly, but I don't want to spend more time on figuring out why
    # yaml is having a hard time serializing
    data = json.loads(to_json(config_dict))
    return yaml.dump(data, default_flow_style=False)

################################################################################

# quick & ugly
class ParseObj():
    """
    Top level parser object.  A quick hack, should convert this to something
    more mainstream, at some point.

    Methods begin with _ as values are stored as attributes on object, for
    convenient in-code use.
    """
    _parent_obj = None
    _parent = None
    _items = None
    _required = {}
    _skel = {}

    def __init__(self, parent=None, keyword='', **kwargs):
        if parent != self:
            self._parent_obj = parent
        if self._items is None:
            self._items = set()
        elif isinstance(self._items, list):
            self._items = set(self._items)
        self._key_rx = re.compile(r'^[A-Za-z0-9+]+$')
        self._key_arg_rx = re.compile(r'^([A-Za-z0-9+]+)\s*\(([A-Za-z0-9-]+)\)$')
        if parent:
            self._parent = parent._parent + "." + keyword # pylint: disable=protected-access
        else:
            self._parent = keyword

    def _skeleton(self):
        #print("SKEL {}".format(self._skel))
        skel = dict()
        for elm, typ in self._skel.items():
        #    print("ELM={} {}".format(elm, typ))
            if isinstance(typ, ParseObj):
        #        print("Is ParseObj")
                skel[elm] = typ._skeleton()
            else:
        #        print("default")
                skel[elm] = typ
        return skel

    def _get(self, key, default=None):
        return self.__dict__.get(key, default)

    def _get_root(self):
        """Walk up the tree and find the root object"""
        if self._parent_obj:
            return self._parent_obj._get_root()
        return self

    def _error(self, msg, *args):
        """Raise an error"""
        abort("{}: {}", self._parent, msg.format(*args))

    def _export(self):
        """Recursively export the tree"""
        exported = dict()
        for key in self._items:
            value = getattr(self, key)
            if isinstance(value, ParseObj):
                value = value._export()
            elif key == 'forms': # earlier iteration of code, stored differently
                new = dict()
                for form in value:
                    new[form] = value[form]._export()
                value = new
            exported[key] = value
        return exported

    def _add_elems(self, src):
        """Add elements from a list of dictionary keypairs"""
        for keypair in src:
            key = list(keypair.keys())[0] # should assert no more keys
            value = keypair[key]
            self._add_key(key, value)
        return self

    def _add_keys(self, src):
        """Add elements from a dictionary"""
        for key, value in src.items():
            self._add_key(key, value)
        return self

    def _add_key(self, key, value):
        """Add element as a key/value"""
        keyarg = False
        if not self._key_rx.match(key):
            match = self._key_arg_rx.match(key)
            if match:
                key = match.group(1)
                keyarg = match.group(2)
            else:
                abort("Invalid keyword at {}.{}", self._parent, key)

        try:
            parse = getattr(self, "_parse_" + key)
        except AttributeError:
            # if you get this, make sure there is a ._parse_{name} function on
            # the respective sub-object
            abort("Unrecognized keyword at {}.{}", self._parent, key)

        self._items.add(key)
        if keyarg:
            setattr(self, key, parse(key, value, arg=keyarg))
        else:
            setattr(self, key, parse(key, value))
        return self

    def _keyname(self, key):
        """return the current key name"""
        return ".".join([self._parent, key])

    def _is_type(self, key, value, etype, none=False):
        """error if type isn't a match; if none=True type can also be None"""
        if not isinstance(value, etype):
            if none and value is None:
                return value
            self._error("{} must be {}, not {}", self._keyname(key), etype, type(value))
        return value

################################################################################
# cleanup dumping of json (sigh)
@singledispatch
def to_serializable(val):
    """Used by default."""
    return str(val)

@to_serializable.register(ParseObj)
# pylint: disable=invalid-name
def serialize_parseObj(val):
    """export a ParseObj properly w/json"""
    return val._export()

################################################################################
def aslist(value):
    """if value is not a list, make it one"""
    if isinstance(value, str):
        return [value]
    return value

################################################################################
class Test(ParseObj):
    _skel = {
        'volumes': list(),
        'input': dict(),
        'expect': list()
    }
    volumes = []
    input = {}
    expect = []

    def __init__(self, key=None, value=None, **kwargs):
        super().__init__(**kwargs)
        if value:
            if isinstance(value, list):
                self._add_elems(value)
            elif isinstance(value, dict):
                self._add_keys(value)

    def _parse_volumes(self, key, value):
        vols = []
        if isinstance(value, str):
            value = [value]
        # we've already processed this -- probably a merge is happening
        if value and isinstance(value[0], dict):
            return value
        for vol in self._is_type(key, value, list):
            path1, path2 = ((vol+"::").split(":"))[0:2]
            if not os.path.exists(path1):
                print("{}.{}: (WARNING) cannot find test volume: {}"
                      .format(self._parent, key, path1))
            vols.append({"src": path1, "dst": path2})
        return vols

    def _parse_input(self, key, value):
        return self._is_type(key, value, dict)

    def _parse_expect(self, key, value):
        return dex_transpile(value)

################################################################################
class Dimensions(ParseObj):
    _skel = {
        'finish': list(),
        'expect': list(),
        'time': ['latest'],
        'geoloc': ['anywhere'],
        'participants': list()
    }
    finish = None
    expect = None

    def __init__(self, key=None, value=None, **kwargs):
        super().__init__(**kwargs)
        if value:
            if isinstance(value, list):
                self._add_elems(value)
            elif isinstance(value, dict):
                self._add_keys(value)
            else:
                self._error("Shouldn't reach this {} {}".format(type(value), value))

    def _parse_time(self, key, value):
        return dex_transpile(value, default_assign='time')

    def _parse_geoloc(self, key, value):
        return dex_transpile(value, default_assign='geoloc')

    def _parse_participants(self, key, value):
        return dex_transpile(value)

    def _parse_finish(self, key, value):
        return dex_transpile(value)
    # this is for globals
    def _parse_expect(self, key, value):
        return dex_transpile(value)


################################################################################
class Form(ParseObj):
    _skel = {
        'extends': list(),
        'dependencies': dict(),
        'purpose': '''
          Example Polyform with several sub-forms
        ''',
        'type': 'runtime',
        'dimensions': Dimensions(),
        'authentication': '',
        'expect': list(),
        'finish': list(),
        'interface': dict(),
        'run': '',
        'example': '',
        'test': dict(),
        'volumes': list(),
        'deploy': list()
    }

    extends = None
    authentication = None
    interface = None
    expect = None
    finish = None
    dimensions = None
    test = None
    volumes = None
    deploy = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._add_key("type", "runtime")
        self._add_key("interface", dict())
        self._add_key("extends", None)
        self._add_key("finish", list())
        self._add_key("expect", list())
        self._add_key("volumes", list())
        self._add_key("dimensions", dict())
        self._add_key("test", dict())

    def _extends(self):
        if self.extends:
            root = self._get_root()
            src = root.forms.get(self.extends)
            if not src:
                self._error("Unable to find form {} to extend from".format(self.extends))

            # deepcopy, because python can't handle immutable dictionaries
            parent = copy.deepcopy(src._export())
            if not parent:
                abort("Cannot extend form '{}'".format(self.extends))
            self_info = copy.deepcopy(self._export())
            new = dictlib.union_setadd(parent, self_info)
            del new['extends']

            # reparse; first remove items from this object, then re-add each
            for item in self._items:
                delattr(self, item)
            self._add_keys(new)

    def _parse_extends(self, key, value):
        return value

    def _parse_dependencies(self, key, value):
        # add/del/list
        return self._is_type(key, value, dict) # TODO

    def _parse_purpose(self, key, value):
        return self._is_type(key, value, str)

    def _parse_type(self, key, value):
        accepted = ("runtime", "training", "template", "codetest", "synthetic")
        if value not in accepted:
            self._error("Invalid type `{}`, not one of: " + ", ".join(accepted), value)
        return value

    def _parse_dimensions(self, key, value):
        return Dimensions(parent=self, keyword="dimensions", key=key, value=value)

    def _parse_authentication(self, key, value):
        return self._is_type(key, value, str, none=True)

    def _parse_expect(self, key, value):
        # TODO: verify DES
        return dex_transpile(value)

    def _parse_finish(self, key, value):
        # TODO: verify DES
        return dex_transpile(value)
        #return self._is_type(key, value, str, none=True)

#    def _parse_result(self, key, value):
#        # TODO: verify DES to GraphQL
#        return self._is_type(key, value, str, none=True)

    def _parse_interface(self, key, value):
        if not value:
            return {}
        if isinstance(value, dict):
            return value
        try:
            parsed = gql_parse.interface(value)
        except gql_parse.GraphQLSyntaxError as err:
            err = str(err).replace("{", "{{").replace("}", "}}")
            self._error("\n  {}:\n!!! {}".format(key, err))
        types = parsed['val']['types']
        for required in ('Input', 'Output'):
            if not types.get(required):
                print("WARNING: {}.{}.{} not defined, defaults to nothing"
                      .format(self._parent, key, required))
                types[required] = {}
        return types

    def _parse_run(self, key, value):
        if value is False:
            return False
        return self._is_type(key, value, str, none=True)
        # TODO: if value is None, set value to function name, needs to be followup

    def _parse_example(self, key, value, arg="unknown"):
        return self._is_type(key, value, str)

    def _parse_test(self, key, value):
        # TODO: verify DES
        return Test(parent=self, keyword="test", key=key, value=value)

    def _parse_volumes(self, key, value):
        vols = []
        if isinstance(value, str):
            value = [value]
        # we've already processed this -- probably a merge is happening
        if value and isinstance(value[0], dict):
            return value
        for vol in self._is_type(key, value, list):
            path1, path2 = ((vol+"::").split(":"))[0:2]
            if not os.path.exists(path1):
                print("{}.{}: (WARNING) cannot find volume: {}"
                      .format(self._parent, key, path1))
            vols.append({"src": path1, "dst": path2})
        return vols

    def _parse_deploy(self, key, value):
        return self._is_type(key, value, dict)

class Resources(ParseObj):
    _skel = {
        'datastores': dict(),
        'plasma': dict(),
        'authentication': dict()
    }

    def __init__(self, key=None, value=None, **kwargs):
        super().__init__(**kwargs)
        if value:
            self._add_keys(self._is_type(key, value, dict))

    def _parse_datastores(self, key, value):
        # for each datastore use a Datastore() object and assure 'role' is defined
        return self._is_type(key, value, dict)

    def _parse_plasma(self, key, value):
        return Plasma(parent=self, keyword="plasma", key=key, value=value)

    def _parse_authentication(self, key, value):
        return self._is_type(key, value, dict)

class Meta(ParseObj):
    _skel = {
        'owner': '',
        'name': '',
        'domain': '',
        'purpose': '',
        'deploy': dict(),
        'language':  'python-3.7',
        'env': list(),
        'market': dict(),
        'dimensions': Dimensions(),
        'dependencies': dict(add=['polyform'])
    }
    language = ''

    def __init__(self, key=None, value=None, **kwargs):
        super().__init__(**kwargs)
        if value:
            self._add_keys(self._is_type(key, value, dict))

    def _parse_owner(self, key, value):
        return self._is_type(key, value, str)

    def _parse_name(self, key, value):
        value = self._is_type(key, value, str)
        if re.search(r'[^a-z0-9_.]', value):
            self._error("{} may only contain a-z 0-9 _ and .", key)
        return value

    def _parse_domain(self, key, value):
        value = self._is_type(key, value, str)
        if re.search(r'[^a-zA-Z0-9-.]', value):
            self._error("{} may only contain a-z A-Z 0-9 - and .", key)
        return value.lower()

    def _parse_purpose(self, key, value):
        return self._is_type(key, value, str)

    def _parse_deploy(self, key, value):
        return self._is_type(key, value, dict)

    def _parse_language(self, key, value):
        self._is_type(key, value, str)
        name, vers = value.split("-")
        major, minor = (vers + ".").split(".")[0:2]
        return Dict(full=value, name=name, ver=vers, major=major, minor=minor, lambci=name + vers)

    def _parse_env(self, key, value):
        return aslist(value)

    def _parse_market(self, key, value):
        return self._is_type(key, value, dict)

    def _parse_dimensions(self, key, value):
        return Dimensions(parent=self, keyword="dimensions", key=key, value=value)

    def _parse_dependencies(self, key, value):
        # add/del/list
        return self._is_type(key, value, dict)

class Plasma(ParseObj):
    _skel = {
        'driver': '',
        'lifecycle': dict(),
        'interval': '',
        'outer': '',
        'updates': dict(),
        'catalog': '',
        'combine': dict(),
        'mapping': ''
    }

    def __init__(self, key=None, value=None, **kwargs):
        super().__init__(**kwargs)
        if value:
            self._add_keys(self._is_type(key, value, dict))

    def _parse_driver(self, key, value):
        return self._is_type(key, value, str)

    def _parse_lifecycle(self, key, value):
        return self._is_type(key, value, dict) # TODO

    def _parse_interval(self, key, value):
        return self._is_type(key, value, str)

    def _parse_outer(self, key, value):
        return self._is_type(key, value, str)

    def _parse_updates(self, key, value): # TODO
        return self._is_type(key, value, dict)

    def _parse_catalog(self, key, value):
        return self._is_type(key, value, str)

    def _parse_combine(self, key, value):
        return self._is_type(key, value, dict)

    def _parse_mapping(self, key, value):
        return self._is_type(key, value, str)

################################################################################
class Polyform(ParseObj):
    """Polyform object type (base)"""
    _required = ["scheme", "meta", "resources", "forms"]
    _skel = {
        'scheme': '1.0',
        'meta': Meta(),
        'resources': Resources(),
        'forms': {'form-name': Form._skeleton(Form)}
    }
    forms = Dict()
    scheme = "1.0"
    meta = Dict(name='')
    resources = Dict()
#    name = None
#    config = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config = kwargs.get('config')

    def _finish(self):
        """Called when the object load is completed"""
        ## TODO: change this to map against default object template function
        for key in self._required:
            try:
                getattr(self, key)
            except: # pylint: disable=bare-except
                abort("missing attribute")

        # handle extends importing
        for key in self.forms:
            self.forms[key]._extends() # pylint: disable=protected-access

        # drop templates
        for key in list(self.forms.keys()):
            if self.forms[key].type == "template" and self.forms.get(key):
                del self.forms[key]
            else:
                # flatten dependencies
                form = self.forms[key]
                deps = form.dependencies.get("add", list())
                for dep in form.dependencies.get("del", []):
                    deps.remove(dep)
                form.dependencies = list(set(GLOBAL_PIP + deps))
                form.dependencies.sort() # so Dockerfile doesn't change signature
                if form.authentication:
                    if not self.resources.authentication.get(form.authentication):
                        # pylint: disable=line-too-long
                        abort("`forms.{}.authentication={}` auth scheme not defined at `resources.authentication.{}`",
                              key, form.authentication, form.authentication)
                if form.dimensions.expect:
                    form.expect = form.dimensions.expect + form.expect
                if form.dimensions.finish:
                    form.finish = form.dimensions.finish + form.finish

        # copy name to a higher level
        #self.name = self.meta.name

        return self

#    def _parse_name(self, key, value):
#        return value

    def _parse_scheme(self, key, value):
        if value != "1.0":
            self._error("scheme is not 1.0", type)
        return value

#    def _parse_owner(self, key, value):
#        return value

    def _parse_meta(self, key, value):
        return Meta(parent=self, keyword="meta", key=key, value=value)

    def _parse_resources(self, key, value):
        return Resources(parent=self, keyword="resources", key=key, value=value)

    # a list of
    def _parse_forms(self, key, value):
        # or make this a sub-class as a list of forms?
        self._is_type(key, value, dict)
        forms = dict()
        for form_key, form_value in value.items():
            form = Form(parent=self, keyword="forms." + form_key)
            form._add_keys(form_value)
            forms[form_key] = form
        return forms


def get_resource_config(resources, role):
    """
    search resource configs for one with named role
    """
    for name in resources:
        conf = resources[name]
        if conf.get('role') == role:
            conf['role'] = name
            return dictlib.Dict(conf)
    return None
