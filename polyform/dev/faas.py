#!/usr/bin/env python3
# vim:set expandtab ts=4 sw=4 ai ft=python:
"""
Copyright 2019 Brandon Gillespie; All rights reserved.

Packaging polyforms.  Currently only in AWS lambdas.

A few things:

* `build` will create a layer for all of the package dependencies for a given function,
  separate from the function itself.  Each ends up at:
  - _build/{functionName}.zip
  - _build/{functionName}-lib.zip
* `src/` is the folder for the function
* Polyform.yml is the definition of the polyform


--
during build, create /polyform as a folder, as a mount of the python polyform module.
However, all that is really used is the `build.py`

"""

import os
import shutil
import copy
import hashlib
import json
from dictlib import Dict
from ..util import osu, datau
from ..util.out import debug, notify, header, error, abort # pylint: disable=unused-import
from . import FOLDER, ENTRY
from ..config import to_yaml

################################################################################
# FaaS wrapper in Docker
class Docker():
    """
    Function as a Service Wrapper.  Eventually switch over to Fission/Kubes.
    For now, just run via AWS Lambdas, and local docker with lambci
    """
    _info = None
    _run = None
    _opts = None
    _env = None
    _rebuild = False
    _build = True

    # pylint: disable=redefined-builtin,too-many-arguments,redefined-outer-name,line-too-long
    def __init__(self, poly=None, type=None, build=True, lang=None, cache=True, clone=None, test=False):
        if clone:
            self.hash = clone.hash
            self._info = copy.deepcopy(clone._info) # pylint: disable=protected-access
            self._run = copy.deepcopy(clone._run) # pylint: disable=protected-access
            self._opts = copy.deepcopy(clone._opts) # pylint: disable=protected-access
            self._env = copy.deepcopy(clone._env) # pylint: disable=protected-access
            # mnts is just a dict, not a Dict()
            self._run.mnts = copy.deepcopy(clone._run.mnts)  # pylint: disable=protected-access
        else:
            # TODO: ideally the hash isn't of the entire config, but only the form in question
            self.hash = hashlib.sha224(to_yaml(poly._config).encode()) # pylint: disable=protected-access
            self._info = Dict(fname='', owd=os.getcwd(), in_build=False,
                              type=type, build=build, lang=lang, poly=poly,
                              test=test)
            self._run = Dict(img='', args=dict(img=list(), cmd=list()))
            self._run['mnts'] = dict() # keep this one a dict
            self._opts = Dict(cache=cache, cleanup=True)
            self._env = dict()
        for key in ('POLYTEST', 'LOGDATA', 'DEBUG', 'AWS_PROFILE', 'AWS_DEFAULT_REGION', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'):
            if os.environ.get(key):
                self._env[key] = os.environ.get(key)
        if not self._opts.cache:
            self._rebuild = True
        if test:
            self._info.test = test
        if build:
            self._info.build = build
        if type:
            self._info.type = type
        if lang:
            self._info.lang = lang
        if poly:
            self._info.poly = poly
        getattr(self, "as_" + self._info.type)()

    def add_mount(self, name, mode="ro", src=None):
        """add to what we want to mount"""
        if src[0:2] == "./":
            src = os.path.join(self._info.owd, src[2:])
        self._run.mnts[name] = dict(mode=mode, src=src)

    def as_lambda(self):
        """aws lambda handler"""
        langstr = self._info.poly.meta.language.lambci

        self.add_mount("/.aws", src=os.path.expanduser("~/.aws"))
        if self._info.build:
            self._run.img = 'lambci/lambda:build-' + langstr
            osu.needs_folder("_build")
            basedir = os.path.dirname(os.path.dirname(__file__))
            self.add_mount("/root/.bashrc", src=os.path.expanduser("~/.bashrc"))
            self.add_mount("/var/task", src=os.path.join(self._info.owd, "src"), mode="rw")
            self.add_mount("/_build", src=os.path.join(self._info.owd, "_build"), mode="rw")
            self.add_mount(FOLDER + "/polyform", src=basedir)
            self._env["POLYFORM_INCEPT"] = FOLDER
        else:
            self._run.img = 'lambci/lambda:' + langstr
            self.add_mount("/var/task", src=os.path.join(self._info.owd, "src"), mode="ro")

    def img_args(self, *args):
        """add args for docker img (different position than cmd)"""
        self._run.args.img.extend(datau.flat_list(*args))
        return self

    def cmd_args(self, *args):
        """add args for docker cmd (different position than img)"""
        self._run.args.cmd.extend(datau.flat_list(*args))
        return self

    def docker_run(self, *args, **pass_args):
        """Setup and execute `docker run ...`"""
        if args:
            self.img_args(*datau.flat_list(*args))
        form = self._info.poly.forms[self._info.fname]
        for vol in form.volumes:
            self.add_mount(vol['dst'], src=vol['src'])
        if self._info.test:
            for vol in form.test.volumes:
                self.add_mount(vol['dst'], src=vol['src'])
            self._env['POLYTEST'] = "true"

        if self._opts.cleanup:
            self.cmd_args("--rm")
        if pass_args:
            self._run.args.img = list()
            serialized = datau.serialize(pass_args)
            self.img_args(*datau.flat_list(
                "bash", "-c",
                "PYTHONPATH=/opt/python:" + FOLDER
                + " python -m polyform." + ENTRY + " " + serialized
            ))
        osu.cmd(self._docker_run(), abort=True)

    def _docker_run(self):
        """The organized args list for docker run"""
        return [osu.getcmd("docker"), "run"] \
          + datau.flat_list(self._run.args.cmd) \
          + datau.flat_list([("-v", vol) for vol in
                             [val['src'] + ":" + dst + ":" + val['mode']
                              for dst, val in self._run.mnts.items()]]) \
          + datau.flat_list([("-e", env) for env in
                             [key + "=" + val for key, val in self._env.items()]]) \
          + [self._run.img] \
          + self._run.args.img

    def docker_build(self, *args):
        """Setup and execute `docker build ...`"""
        osu.cmdx(self._docker_build(*args))

    def _docker_build(self, *args):
        """The organized args list for docker build"""
        args = datau.flat_list(*args)
        if self._rebuild:
            args = ["--no-cache"] + args
        return [osu.getcmd("docker"), "build"] + args

    def needs_polyconfig(self, form_name=None):
        """generate the polyconfig json"""
        config = export_polyconfig(self._info.poly, form_name)
        with open(os.path.join(self._info.owd, "src", "_polyform.json"), "w") as outf:
            outf.write(json.dumps(config))

    def needs_deps(self, form_name=None):
        """Build if needed, and add the deps mountpoint, for this FaaS"""
        if form_name:
            self._info.fname = form_name
        elif not self._info.fname:
            abort("needs_deps called but no form name defined")
        else:
            form_name = self._info.fname

        self.needs_polyconfig(form_name)
        if self._rebuild or not self.has_build_files() or not self.has_deps_files():
            self._rebuild = True
            if self._info.in_build:
                raise ValueError("Trying to call build from within build?")
            builder = Docker(clone=self, build=True)
            builder.build(form_name) # pylint: disable=not-callable

        # build makes the _deps
        self.add_mount("/opt", src=self._info.owd + "/_deps/" + form_name, mode="ro")
#        self.add_mount("/_deps", src=self.info.owd + "/_deps/" + form_name, mode="ro")
        self._env["PYTHONPATH"] = "/opt/python:/_incept/"
        return self

    def update_hashes(self, form_name, label):
        """update the "hash" file stored alongside a build file"""
        # TODO: rename externally linked cksum file; merge cksum into hash and rename
#        path = os.path.join(self.info.owd, "_build", form_name, label) #  + ".hash")
#        try:
#            dest = readlink(path + ".latest.zip")
#        except:
#            self.exit("Unable to read link for {}.latest.zip".format(path))
#
#        bdest = os.path.basename(dest)
#        match = re.match('^' + label + '\.([a-z0-9])\.zip', dest)
#        if not match:
#            self.exit("Unable to parse destination file {}".format(bdest))
#        hash = match.group(1)
#        if hash != self.hash.hexdigest():
#
#        #bpath = os.path.basename(path)
#
#        self.hash.update(dest)

        path = os.path.join(self._info.owd, "_build", form_name, label  + ".hash")
        with open(path, "w") as outfile:
            outfile.write(self.hash.hexdigest())

    def has_build_files(self):
        """Do we have the latest layer files?"""
        for label in ('libs', 'func'):
            path = os.path.join("_build", self._info.fname, label + ".latest.zip")
            if not os.path.exists(path):
                return False
            hashfile = os.path.join("_build", self._info.fname, label + ".hash")
            if not os.path.exists(hashfile):
                return False
            with open(hashfile) as hfd:
                hash = hfd.read()
            if hash != self.hash.hexdigest():
                return False
        return True

    def has_deps_files(self):
        """Do we have the latest deps unzipped?"""
        if self._rebuild:
            return False
        return os.path.exists(os.path.join("_deps", self._info.fname, "python"))

    def codetest_poly(self):
        """Call the testing suite from within a container"""
        form_name = "codetest"
        self.needs_deps(form_name)
        form = self._info.poly.forms[form_name]
        self.docker_run(exec="test_poly", func=self._info.poly.meta.name, form=form._export()) # pylint: disable=protected-access

#    def functest_poly(self):
#        """Run a functional test, with mock data"""
##        form_name = "test"
#        self.needs_deps(form_name)
#        form = self._info.poly.forms[form_name]
#        self.docker_run(exec="test_poly", func=self._info.poly.meta.name, form=form._export()) # pylint: disable=protected-access

    def dockerfile(self, build_dir, form_name):
        """
        Generate a FaaS dockerfile for building, and check that the image
        has been built.  Return False,False if no changes are needed, or
        dockerfile and a target name if so
        """
        dockerfile = os.path.join(build_dir, "Dockerfile")
        # TODO: resolve collision potential, but this is only intended for local dev work
        dockerfile_deps = dockerfile + ".deps"
        dockerfile_deps_new = dockerfile_deps + ".new"
        base = os.path.basename(self._info.owd)
        form = self._info.poly.forms[form_name]
        with open(dockerfile_deps_new, "w") as outf:
            outf.write("FROM {}\n".format(self._run.img))
            outf.write("RUN rm -rf /_deps/python && mkdir -p /_deps/python &&\\\n")
            outf.write("    pip3 install -t /_deps/python '{}'\n"
                       .format("' '".join(form.dependencies)))

        # do not differ, and image exists as :latest
        tname = (base + "_" + form_name).lower().replace("-", "_")
        while tname[0] == "_":
            tname = tname[1:]
        if self._opts.cache and \
            osu.cmd("diff -q {} {} >/dev/null 2>&1".format(dockerfile_deps, dockerfile_deps_new)):
            if osu.cmd("docker image inspect " + tname + ":latest >/dev/null 2>&1"):
                notify("Using cached image, if not desired, try --no-cache")
                os.unlink(dockerfile_deps_new)
                return False, tname

        # TODO: Use self.hash instead
        _status, out = osu.cmd_outx(["cksum", dockerfile_deps_new])
        os.rename(dockerfile_deps_new, dockerfile_deps)
        self.needs_polyconfig(form_name)
        with open(dockerfile, "w") as outf, open(dockerfile_deps, "r") as deps:
            outf.writelines(deps.readlines())
            outf.write("COPY _polyform.json .\n")
            outf.write("RUN echo {} >> /_deps/.cksum\n".format(out.split(" ")[0]))
        return dockerfile, tname

    def build(self, form_name):
        """
        Build a polyform
        """
        self._info.fname = form_name
        self._info['in_build'] = True
        if not self._info.build:
            abort("Cannot build an image not configured for dev")
        form = self._info.poly.forms[form_name]
        build_d = "_build" + os.sep + form_name
        osu.needs_folder(build_d)

        # build libs in docker container
        dockerfile, tname = self.dockerfile(build_d, form_name)
        if dockerfile:
            osu.must_chdir(os.path.join(self._info.owd, "src"))
            dockerfile = os.path.join("../", dockerfile)
            self.docker_build("-f", dockerfile, ".", "-t", tname)

        # what if dockerfile=false?
        if not self.has_build_files():
            # build function
            self._run.img = tname
            self.docker_run(exec="export_zips", func=form_name, form=form._export()) # pylint: disable=protected-access
            self.update_hashes(form_name, "libs")
            self.update_hashes(form_name, "func")

        # unzip into _exec
        # Check the version# first
        if not self.has_deps_files():
            deps_target = "./_deps/" + form_name
            os.chdir(self._info.owd)
            if os.path.exists(deps_target):
                shutil.rmtree(deps_target)

            osu.needs_folder(deps_target)
            osu.must_chdir(deps_target)
            srczip = "../../_build/" + form_name + "/libs.latest.zip"
            header("Unzipping {} -> {}".format(srczip, deps_target))
            osu.cmd(["unzip", "-q", srczip])

        self._info['in_build'] = False

class FaaS(Docker):
    """placeholder: In the future make this more abstract"""

################################################################################
def export_polyconfig(poly, form):
    """create a trimmed polyform config and store it as json, to go within the func.zip"""
    config = poly._export() # pylint: disable=protected-access
    config['target'] = form
    fobj = config['forms'][form]
    config['forms'] = Dict()
    config['forms'][form] = fobj
    rds = config['resources']['datastores']
    for name in rds:
        for key in list(rds[name].keys()):
            if key not in ('role', 'driver', 'config'):
                del rds[name][key]
    return config
