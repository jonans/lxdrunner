#!/usr/bin/env python3

import os
import os.path
import time
import logging
import pathlib

import pylxd
import pylxd.exceptions

from .applog import log
from .appconf import config as cfg
from . import util


class LXDRunner:
    def __init__(self, connect=True):
        self.client = None
        if connect:
            self.connect()

    def connect(self):
        self.client = pylxd.Client()

    def pushfile(self, src, instance, dst, **exargs):
        " Push file into instance "
        log.info("Pushing: %s to %s", src, dst)
        with open(src, "rb") as fp:
            instance.files.put(dst, fp.read(), **exargs)

    def get_workers(self):
        " Return LXD instances that are workers "
        return [
            wrkr for wrkr in self.client.instances.all()
            if util.has_prefix(wrkr.name)
        ]

    def script_env(self, evt, instname: str):
        "Setup environment variables for runner script"

        return dict(
            GHA_TOKEN=evt.token,
            GHA_URL=evt.target_url,
            GHA_NAME=instname,
            GHA_EXTRA_LABELS=",".join(evt.rc.labels),
        )

    def launch_instance(self, inst_name: str, rc):
        " Launch container/vm instance with given name and config "

        instcfg = dict(
            name=inst_name,
            ephemeral=True,
            profiles=rc.profiles,
            source=dict(type="image", alias=rc.image),
            type=rc.type
        )
        log.warning("Launching instance %s", inst_name)
        inst = self.client.instances.create(instcfg, wait=True)
        inst.start(wait=True)
        return inst

    def start_gha_runner(self, inst, evt):

        pkg = evt.pkg

        installdir = pathlib.Path("/opt/runner")
        pkg_src = os.path.join(cfg.pkgdir, pkg.linkname)
        pkg_dst = os.path.join(installdir, "actions-runner.tgz")
        script_dst = installdir.joinpath(evt.rc.setup_script.name)
        vars_dst = installdir.joinpath("setupvars.conf")
        # Setup env vars for script
        environment = self.script_env(evt, inst.name)

        # VMs are slow to become available. Retry until
        # agent responds.
        for num in range(15):
            try:
                inst.files.mk_dir(installdir, mode="0755")
                log.info("Make dir: %s", installdir)
                break
            except Exception:
                time.sleep(5)

            if num >= 14:
                log.warning("Runner start timeout, destroying %s", inst.name)
                inst.stop(force=True)
                return

        # Push runner setup script to instance
        self.pushfile(evt.rc.setup_script, inst, script_dst, mode="0755")
        inst.files.put(vars_dst, util.env_str(environment), mode="0755")
        self.pushfile(pkg_src, inst, pkg_dst, mode="0755")

        # Execute runner setup script
        log.info(f"Executing: {script_dst}")
        (exitcode, stdout,
         stderr) = inst.execute([str(script_dst)], environment=environment)
        if exitcode or log.level <= logging.DEBUG:
            log.error("===STDOUT====\n%s", stdout)
            log.error("===STDERR====\n%s", stderr)
        if exitcode:
            raise Exception(f"Provisioner exit code: {exitcode}")

        log.info("Provision sucesssful")

    def verify_launch(self, evt):
        errs = []
        try:
            self.client.images.get_by_alias(evt.rc.image)
        except pylxd.exceptions.NotFound:
            errs.append(f"image does not exist: {evt.rc.image}")
        for prof in evt.rc.profiles:
            if not self.client.profiles.exists(prof):
                errs.append(f"profile does not exist: {prof}")
        if not evt.rc.setup_script.exists():
            errs.append(f"script does not exist: {evt.rc.setup_script}")
        if errs:
            for err in errs:
                log.error("Error: %s", err)
            return False
        return True

    def _cleanup_instance(self, inst_name):
        if not cfg.cleanup:
            log.error("Runner start failed, CLEANUP DISABLED")
            return False
        log.error("Runner start failed, destroying %s", inst_name)

        try:
            inst = self.client.instances.get(inst_name)
            inst.stop()
            inst.delete()
        except pylxd.exceptions.LXDAPIException:
            return False
        return True

    def _thread_launch(self, evt):
        " Launch GHA Runner in thread"

        # FIX ME ! PyLXD is probably not thread safe "

        def run(evt):
            lxd = LXDRunner()
            lxd._launch(evt)

        log.info(f"Thread start {evt.check_run_id}")
        util.threadit(run, args=(evt, ))

    def _launch(self, evt):
        " Launch GHA Runner, main method "
        instname = util.make_name()

        if not self.verify_launch(evt):
            return False
        # Any error here needs instance cleanup
        try:
            inst = self.launch_instance(instname, evt.rc)
            self.start_gha_runner(inst, evt)
        except Exception as exc:
            log.exception(exc)
            self._cleanup_instance(instname)
            return False
        return True

    def launch(self, evt, wait=False):
        " Launch GHA Runner "
        # FIX ME ! PyLXD is probably not thread safe "
        if not wait:
            self._thread_launch(evt)
        else:
            self._launch(evt)
