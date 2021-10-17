#!/usr/bin/env python3

import json
import logging
import os
import os.path
import pathlib
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import pylxd
import pylxd.exceptions
import urllib3

from . import util
from .appconf import config as cfg
from .applog import log

urllib3.disable_warnings()


def get_client(rname="main", verify=False):
    cert = None
    remote = cfg.remotes.get(rname)
    if remote.addr and remote.addr.startswith("https://"):
        cert = cfg.key_pair_paths()

    log.info(f"Connecting to LXD: {remote.addr or 'local unix-socket'}")
    return pylxd.Client(endpoint=remote.addr, cert=cert, verify=verify)


class LXDRunner:
    def __init__(self, connect=True):
        self.client = None
        if connect:
            self.connect()

        self.workers = dict()
        self.pool = ThreadPoolExecutor(cfg.max_workers)

    def connect(self):
        self.client = get_client("main")

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

    def worker_count(self):
        return len(self.workers)

    def status(self):
        return f"{ len(self.workers) } workers"

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
            source=util.image_to_source(rc.image),
            type=rc.type
        )
        log.warning("Launching instance %s", inst_name)
        inst = self.client.instances.create(instcfg, wait=True)
        inst.start(wait=True)
        return inst

    def start_gha_runner(self, inst, evt):

        pkg = evt.pkg

        installdir = pathlib.Path("/opt/runner")
        pkg_src = os.path.join(str(cfg.dirs.pkgdir), pkg.linkname)
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
            if ":" not in evt.rc.image:
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

    def _launch(self, evt):
        " Launch GHA Runner, main method "

        if "ThreadPool" in threading.current_thread().name:
            threading.current_thread().setName(evt.instname)

        self.workers[evt.instname] = evt
        if not self.verify_launch(evt):
            return False
        # Any error here needs instance cleanup
        noerror = True
        try:
            inst = self.launch_instance(evt.instname, evt.rc)
            self.start_gha_runner(inst, evt)
        except Exception as exc:
            log.exception(exc)
            self._cleanup_instance(evt.instname)
            noerror = False

        return noerror

    def launch(self, evt, wait=False):
        " Launch GHA Runner "

        def handle_done(futr):
            err = futr.exception()
            if not err:
                return
            raise err

        if not wait:
            self.pool.submit(self._launch, evt).add_done_callback(handle_done)
        else:
            self._launch(evt)

    def start_tasks(self):
        util.threadit(self.watch_lxd_events, name='LXD-Events')

    def watch_lxd_events(self):

        client = get_client('main')

        ## Workaround for bug in pylxd 2.3.0 : WSS not using certs
        ssl_options = {}
        if client.api.scheme == 'https':
            ssl_options.update(
                {
                    "certfile": client.cert[0],
                    "keyfile": client.cert[1]
                }
            )

        class FixedWSClient(pylxd.client._WebsocketClient):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs, ssl_options=ssl_options)

        ## END workaround

        def process_message(message):
            if message.is_text:
                message = json.loads(message.data)
            if message["metadata"]["action"] == "instance-deleted":
                instname = message["metadata"]["source"].split("/")[-1]
                if not util.has_prefix(instname):
                    return
                try:
                    job = self.workers.pop(instname, None)
                    log.info(f"Removing {instname} {self.status()}")
                    if job:
                        job.rc.worksem.release()
                except ValueError:
                    log.error("Semaphore release fail", instname)
            pass

        evfilter = set([pylxd.EventType.Lifecycle])
        ws_client = client.events(
            event_types=evfilter, websocket_client=FixedWSClient
        )
        ws_client.received_message = process_message
        ws_client.connect()
        ws_client.run()
