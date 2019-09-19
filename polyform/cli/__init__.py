#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Data Universe Polyforms FTW

"""

import sys
import os
import re

import dictlib
import yaml
from ..config import Config, to_yaml, to_json
from ..util import osu
from ..util.out import debug, notify, header, error, abort # pylint: disable=unused-import
from ..dev.faas import FaaS
from . import argp, auth, dudb, sls
#from ..provider.aws import s3, dynamo

################################################################################
class PolyformCli():
    """
    General class for handling `poly` commands
    """
    base = None
    cfg = None
    args = None
    polyform = None

    # pylint: disable=no-member
    def __init__(self):
        self.base = dict(aws=dict(profile='', region=''))
        rcpath = os.path.expanduser("~/.polyrc")
        if os.path.exists(rcpath):
            with open(rcpath) as infile:
                load = yaml.full_load(infile)
                if load:
                    self.base.update(load)
        self.base = dictlib.Dict(self.base)
        if not self.base.get('aws'):
            print("WARNING: AWS doesn't appear configured: try `poly setup`")
        else:
            for key, env in [['profile', 'AWS_PROFILE'], ['region', 'AWS_DEFAULT_REGION']]:
                if not os.environ.get(env) and self.base.aws.get(key):
                    os.environ[env] = self.base.aws.get(key)
#                    print("exporting {}={}".format(env, os.environ[env]))
        os.environ['PYTHONUNBUFFERED'] = 'true'

    ############################################################################
    def _needs_config(self):
        """abort if the polyform configuration is not loaded"""
        self.cfg = Config(path=self.args.config)
        self.polyform = self.cfg.polyform
        if self.cfg.polyform is None:
            abort("No Polyform.yml in current folder")

    ############################################################################
    def _next_arg(self):
        """grab the next argument.  kindof hacky"""
        if len(self.args.args) > 0: # pylint: disable=len-as-condition
            first = self.args.args[0]
            self.args.args = self.args.args[1:]
            return first
        return ""

    ############################################################################
    def _get_form(self, cmd):
        """
        Lookup a polyform from the configuration, or abort with an error.
        """
        forms = list(self.polyform.forms.keys())
        arg = self._next_arg()
        if arg not in forms:
            forms = [form for form in forms if form != 'codetest']
            argp.syntax("Where {form} is one of: " + ", ".join(forms), args=cmd + " {form}")
        return arg

    ############################################################################
    def _get_func_module(self): # pylint: disable=inconsistent-return-statements
        name = self.polyform.meta.name
        for fpath in [("src", name + ".py"),
                      ("src", name, "__init__.py")]:
            path = os.path.join(*fpath)
            if os.path.exists(path):
                return name, path

        abort("Missing src/{name}.py or src/{name}/__init__.py".format(name=name))

    ############################################################################
    def cmd(self):
        """
        Run a command in CLI form, using this object, uses sys.argv.  The first
        arg of the command line is the action, which becomes `this.cmd_{ACTION}`
        """
        parser = argp.argparse_class_methods(PolyformCli, self, "cmd_")

        parser.add_argument("--lane", choices=["local"], default="local")
        parser.add_argument("--config")
        parser.add_argument("--no-cache", action='store_true')
        parser.add_argument("--debug", action='store_true')
        parser.add_argument("--output", "-o", default="yaml")
        self.args = parser.parse_args()

        # TODO: not sure why argparse isn't catching this
        if not self.args.__dict__.get("func"):
            parser.print_help(sys.stderr)
            sys.exit(1)

        if self.args.debug:
            os.environ["DEBUG"] = "True"

        try:
            self.args.func()
            if os.path.exists("src/_polyform.json"):
                os.unlink("src/_polyform.json")
        except KeyboardInterrupt:
            return

    ############################################################################
    def _get_form_run(self, name):
        default = "$self.$form()"
        try:
            form = self.polyform.forms[name]
        except: # pylint: disable=bare-except
            sys.exit("Cannot find form `{}`".format(name))
        run = form._get("run") # pylint: disable=protected-access
        if run is False:
            notify("Function `{}` is specified as non-runnable")
            return False
        if not run:
            run = default

        run = re.sub(r'\s+#.*$', "", run)
        run = run.replace("$self.", "") # not really needed
        run = run.replace("$form", name)
        run = re.sub(r'\(\s*\)\s*$', "", run)

        return run

    def cmd_check(self):
        """
        `poly check`

        Review the configuration, check the function matches the config.
        """
        self._needs_config()
        func, _path = self._get_func_module()
        sys.path.append("src")
#        import importlib
#        importlib.invalidate_caches()
#        mod = importlib.import_module(func)
#        modd = mod.__dict__
#        print(modd.keys())

        notify("WARNING: This is incomplete, and doesn't validate yet")
        trim_rx = re.compile(r'^' + func + '\\.')
        for form in self.polyform.forms:
            if form == 'codetest':
                continue

            run = self._get_form_run(form)
            run = func + "." + trim_rx.sub('', run)
            print("{}.forms.{}: run: {}()".format(self.polyform.meta.name, form, run))

            #splits = run.split(".")
            #ifunc = splits[-1]
            #modname = ".".join(splits[0:-1])

            # TODO: running into problems with this outside the container,
            # when local deps are not defined.  When time allows look into
            # using lower level __import__ and specifying a bogus list of
            # locals which include the deps its looking for
#            importlib.invalidate_caches()
#            spec = importlib.util.find_spec(modname)
#            spec = importlib.util.find_spec(run)
#            print(spec)
#            modd = mod.__dict__
#            if spec.get(ifunc):
#                notify("EXISTS  {}()".format(run))
#            else:
#                notify("MISSING {}()".format(run))

    ############################################################################
    def cmd_inspect(self):
        """
        `poly inspect`

        Review the polyform configuration and correlate it to the function
        """
        self._needs_config()
        arg = self._next_arg()
        # TODO: Need to cleanup things so this isn't as painful to traverse
        poly = self.polyform._export() # pylint: disable=protected-access
        if arg:
            try:
                poly = {arg: dictlib.dig(poly, arg)}
            except KeyError as err:
                sys.exit("Cannot find key {} from requested keys `{}`".format(err, arg))
        if self.args.output.lower() in ["yaml", "yml", "y"]:
            notify(to_yaml(poly)) # self.cfg.to_yaml())
        else:
            notify(to_json(poly, indent=2))

    ############################################################################
    def cmd_init(self):
        """
        `poly init`

        Initialize a polyform with boilerplate files and folders

        Parameters
        ----------
        form_name : str
            The name of the new polyform to initialize.
        """

        arg = self._next_arg()
        if not arg:
            argp.syntax("Missing desired function name", args="init {form_name}")

        from . import create
        create.new(arg)

    ############################################################################
    def cmd_build(self):
        """
        `poly build {form_name}`

        Build the layers needed to execute polyform function
        """
        self._needs_config()
        form = self._get_form("build")
        poly = self.polyform
        # pylint: disable=not-callable
        FaaS(poly=poly, type="lambda", cache=not self.args.no_cache).build(form)

    ############################################################################
    def cmd_codetest(self):
        """
        `poly codetest` - run lint and doctests which are within your code
        """
        self._needs_config()
        self._get_func_module()
        FaaS(poly=self.polyform, type="lambda", cache=not self.args.no_cache).codetest_poly()

    ############################################################################
    def cmd_functest(self):
        """
        `poly functest` - run a functional test (the application with test data)
        """
        self._needs_config()
        form = self._get_form("functest")
        faas = FaaS(poly=self.polyform, type="lambda", cache=not self.args.no_cache,
                    build=False, test=True)
        faas.needs_deps(form)
        faas.docker_run(self._get_form_run(form))

    ############################################################################
    def cmd_run(self):
        """
        `poly run {form_name}`
        """
        self._needs_config()
        form = self._get_form("run")
        faas = FaaS(poly=self.polyform, type="lambda", cache=not self.args.no_cache,
                    build=False, test=True)
        faas.needs_deps(form)
        faas.docker_run(self._get_form_run(form), *self.args.args)

    ############################################################################
    def cmd_repl(self):
        """
        `poly repl {form_name}`

        Get a language prompt (Read-Eval-Print-Loop) in a container as the
        {form_name} would be running.  I.e. python, node, etc.
        """
        self._needs_config()
        form = self._get_form("repl")
        faas = FaaS(poly=self.polyform, type="lambda", cache=not self.args.no_cache)
        faas.needs_deps(form).cmd_args(["-it"]).docker_run(self.polyform.meta.language.name)

    ############################################################################
    def cmd_sh(self):
        """
        `poly sh {form_name}`

        Get a shell in a container as the {form_name} would be running.
        """
        self._needs_config()
        form = self._get_form("sh")
        faas = FaaS(poly=self.polyform, type="lambda", cache=not self.args.no_cache)
        # go to list so we can expand it to nothing if no args are present;
        # sending in "" as an arg causes problems
        xtra = " ".join(self.args.args)
        if xtra:
            xtra = [xtra]
        else:
            xtra = ["/bin/bash"]
        faas.needs_deps(form).cmd_args(["-it"]).docker_run(*xtra)

    ############################################################################
    def _modcmd_with_resource(self, bobj, cmd, *args):
        self._needs_config()
#        getattr(lambda_dynamo, 'cmd_' + cmd)(self.polyform.resources.datastores, *args)
        getattr(bobj, 'cmd_' + cmd)(self.polyform.resources.datastores, *args)

    ############################################################################
    def cmd_provision(self):
        """
        `poly deprovision` - provision foundational elements in AWS
        """
        for clas in (sls, auth): #, dudb, sls):
            print("--> Provision " + clas.__class__.__name__)
            self._modcmd_with_resource(clas, 'provision')

    def cmd_deprovision(self):
        """
        `poly deprovision` - deprovision foundational elements in AWS
        """
        for clas in (sls,): # auth, dudb, sls):
            print("--> Deprovision " + clas.__name__)
            self._modcmd_with_resource(clas, 'deprovision')

    ############################################################################
    def cmd_deploy(self):
        """
        `poly deploy {form_name}` deploy last build to aws
        """
        self._needs_config()
        target = self._get_form('deploy')
        handler = self._get_form_run(target)
        sls.cmd_deploy(self.cfg.polyform, target, handler)

    ############################################################################
    def cmd_apikey_new(self):
        """
        create a new polyform APIkey
        """
        self._modcmd_with_resource(auth, 'apikey_new')

    def cmd_apikey_ls(self):
        """
        list polyform APIkeys
        """
        self._modcmd_with_resource(auth, 'apikey_ls')

    def cmd_apikey_del(self):
        """
        delete polyform APIkey
        """
        self._modcmd_with_resource(auth, 'apikey_del', *self.args.args)

    def cmd_node_push(self):
        """
        `node-push ID {path-to-upload-file}`
        """
        duid = self._next_arg()
        #duid, element = (ref + ".").split(".")[0:2]
        path = self._next_arg()
        if not os.path.exists(path):
            argp.syntax("Cannot find source file to upload from: {}".format(path))
        self._modcmd_with_resource(dudb, 'node_push', duid, path)

    def cmd_node_pull(self):
        """
        `node-pull ID`
        """
        duid = self._next_arg()
        #duid, element = (ref + ".").split(".")[0:2]
        self._modcmd_with_resource(dudb, 'node_pull', duid)

    ############################################################################
    def cmd_setup(self):
        """
        `setup` - interactive setup for `poly` command
        """

        awscpath = os.path.expanduser("~/.aws/credentials")
        if not os.path.exists(awscpath):
            sys.exit("Cannot find ~/.aws/credentials, make sure it is setup first")
        import configparser
        awscfg = configparser.ConfigParser()
        awscfg.read(awscpath)
        profiles = awscfg.sections()

        # TODO: DRY this out, pull in reflex cfg stuff for encrypted cfg file
        default = self.base.aws.profile
        if default not in profiles:
            default = ''
        val = ''
        while not val:
            val = input("\nAWS Profile [{}] ".format(default))
            if not val and default:
                val = default
            if val not in profiles:
                print("\nProfile `{}` does not exist in ~/.aws/credentials!\n\nTry one of: {}"
                      .format(val, ", ".join(profiles)))
                val = ''
        self.base.aws.profile = val
        default = self.base.aws.region
        val = ''
        while not val:
            val = input("\nAWS Region [{}] ".format(default))
            if not val and default:
                val = default
        self.base.aws.region = val
        with open(os.path.expanduser("~/.polyrc"), "w") as outfile:
            yaml.dump(self.base.__export__(), outfile)

    ############################################################################
    def cmd_pdev_hardlink(self):
        """
        Polyform library development shunt.

        A hack to speedup the dev cycle when working on the polyform library
        """
        # DRY this out: similar code in test.py
        self._needs_config()
        form = self._get_form("pdev-hardlink")

        notify("""
        Proceed only if you know what you are doing.

        This creates hard links from the polyform package into the deps folder,
        which is mounted into containers.
        """)

        deps_target = "./_deps/" + form + "/python/polyform"
        if os.path.exists(deps_target):
            import shutil
            shutil.rmtree(deps_target)
        osu.needs_folder(deps_target)

        base = os.path.dirname(os.path.dirname(__file__))
        srclen = len(base) + 1

        for root, dirname, files in os.walk(base):
            for file in files:
                if file == "__pycache__" or file[-4:] == ".pyc":
                    continue
                srcpath = os.path.join(root, file)
                modpath = deps_target + "/" + srcpath[srclen:]
                dirname = os.path.dirname(modpath)
                osu.needs_folder(dirname)
                notify("{} -> {}".format(srcpath, modpath))
                os.link(srcpath, modpath)

################################################################################
# pylint: disable=missing-docstring
def entrypoint():
    PolyformCli().cmd() # run as an object instance
