#!/usr/bin/env python3

import os
import os.path
import time
import urllib.request
import datetime
import queue
import sched
import tempfile

from ghapi.all import GhApi
import fastcore.net
import schedule

from .applog import log
from .appconf import config as cfg

from . import web
from . import lxd
from . import util
from . import dtypes

#
# Classes
#


class RunManager:
    " LXDRunner Management Class "

    def __init__(self):
        self.ghapi = GhApi(token=cfg.pat)
        self.lxd = lxd.LXDRunner(connect=False)
        self.schedq = sched.scheduler()
        self.evtq = queue.PriorityQueue()
        self.runnermap = {item.labels: item for item in cfg.runnermap}
        # For testing
        # self.activecfg = cfg.activecfg

        # Cache for various github resources
        self.reg_tokens = {}
        self.orgs = []
        self.repos = []
        self.pkgs = []

        return

    def get_repos(self):
        " Get and cache Github repos for user "
        self.repos = self.ghapi.repos.list_for_authenticated_user()
        return self.repos

    def get_orgs(self):
        " Get and cache  Github orgs for user "
        self.orgs = self.ghapi.orgs.list_for_authenticated_user()
        return self.orgs

    def get_runners(self, ghargs):
        " Get registered runners for org or repo "

        if ghargs.get("org"):
            apifunc = self.ghapi.actions.list_self_hosted_runners_for_org
        else:
            apifunc = self.ghapi.actions.list_self_hosted_runners_for_repo

        return apifunc(**ghargs)

    def get_token(self, ghargs):
        " Request or return token from cache "

        tkey = ghargs.get('target')
        token = self.reg_tokens.get(tkey)

        def valid_mins(token):
            td = (
                datetime.datetime.fromisoformat(token.expires_at) -
                datetime.datetime.now().astimezone()
            )
            return td.total_seconds() / 60

        if not token or valid_mins(token) <= 30:
            if ghargs.get("org"):
                log.info("Getting GHA token org: %s", tkey)
                apifunc = self.ghapi.actions.create_registration_token_for_org
            else:
                log.info("Getting GHA token repo: %s", tkey)
                apifunc = self.ghapi.actions.create_registration_token_for_repo

            self.reg_tokens[tkey] = token = apifunc(**ghargs)

        return token

    def get_queued_runs_for_repo(self, owner, repo, **kwargs):
        """ Get queued workflow with check runs for given repo
        Return list(workflow_runs) with .check_runs set to corresponding
        check_runs.
        """
        #
        # actions.list_workflow_runs_for_repo(
        #  owner, repo, actor, branch, event, status, per_page, page)
        # checks.list_for_suite(
        #  owner, repo, check_suite_id, check_name, status, filter, per_page,
        #   page)
        #
        # Get queued workflows
        # Use workflow checksuite_id to lookup check_runs
        target = dict(owner=owner, repo=repo, status='queued')

        wf_runs = self.ghapi.actions.list_workflow_runs_for_repo(
            **target
        ).workflow_runs

        for run in wf_runs:
            run.check_runs = self.ghapi.checks.list_for_suite(
                **target, check_suite_id=run.check_suite_id
            ).check_runs
        return wf_runs

    def get_queued_runs(self):
        " Get queued workflow with check runs from all repos "
        self.get_repos()

        runs = []
        for repo in self.repos:
            runs += self.get_queued_runs_for_repo(repo.owner.login, repo.name)
        return runs

    def submit_pending_runs(self):
        events = []
        wfruns = self.get_queued_runs()
        for wfrun in wfruns:
            for ckrun in wfrun.check_runs:
                org = ''
                if wfrun.repository.owner.type == 'Organization':
                    org = wfrun.repository.owner.login
                events.append(
                    dict(
                        check_run_id=ckrun.id,
                        repo=wfrun.repository.name,
                        owner=wfrun.repository.owner.login,
                        org=org
                    )
                )
        log.warning("Submitted %s pending run events", len(events))
        for evt in events:
            self.queue_evt(evt)

    def get_runner_pkg(self, rc):
        " Get runner package for given runner config "

        return next(
            filter(
                lambda pkg: (pkg.os, pkg.architecture) ==
                (rc.runner_os, rc.runner_arch), self.pkgs
            )
        )

    def get_packages(self):
        " Get list of runner packages from actions/runner releases"

        def asset2pkg(asset):
            " Convert release assets to obj like list_runner_applications "
            parts = asset.name.split('-')
            os, arch = parts[2:4]
            linkname = "-".join(parts[:4] + ["latest"])
            return dtypes.RunnerPackage(
                filename=asset.name,
                linkname=linkname,
                os=os,
                architecture=arch,
                download_url=asset.browser_download_url
            )

        rels = self.ghapi.repos.list_releases('actions', 'runner')
        rels = rels.filter(lambda rel: not rel.prerelease)
        self.pkgs = list(map(asset2pkg, rels[0].assets))
        return self.pkgs

    @schedule.repeat(schedule.every().day)
    def update_pkg_cache(self):
        " Update runner package cache to latest version "

        log.info("Updating runner package cache")

        self.get_packages()

        if not os.path.exists(cfg.pkgdir):
            os.makedirs(cfg.pkgdir)

        pkgfiles = set()

        for pkg in self.pkgs:
            pkgfiles.update((pkg.filename, pkg.linkname))
            filepath = os.path.join(cfg.pkgdir, pkg.filename)
            linkpath = os.path.join(cfg.pkgdir, pkg.linkname)

            if not os.path.exists(filepath):
                log.info("Downloading: " + pkg.filename)
                urllib.request.urlretrieve(pkg.download_url, filepath)

            # Create a symlink to runner package making it available
            # under a persistent name. In the event pkg is updated
            # during launch event.

            # Create temp name for symlink
            temp_linkpath = tempfile.mktemp(dir=cfg.pkgdir)
            # Symlink to pkg.filename
            os.symlink(pkg.filename, temp_linkpath)
            # Atomic replace existing symlink
            os.replace(temp_linkpath, linkpath)

        dirfiles = set(os.listdir(cfg.pkgdir))
        delfiles = dirfiles - pkgfiles

        for fname in delfiles:
            log.info(f"Deleting : {fname}")
            os.unlink(os.path.join(cfg.pkgdir, fname))

    def cleanup_runners(self, ghargs):
        " Delete offline runners for given org or repo "

        try:
            runners = self.get_runners(ghargs)
        except fastcore.net.ExceptionsHTTP[403]:
            log.warning(f"Get Runners: Access Denied { ghargs }")
            return

        runners = [
            run for run in runners.runners
            if run.status == "offline" and util.has_prefix(run.name)
        ]

        for run in runners:
            ghargs['runner_id'] = run.id
            if ghargs.get("org"):
                log.info(
                    "Remove offline runner {org} {runner_id}".format(
                        **ghargs
                    )
                )
                self.ghapi.actions.delete_self_hosted_runner_from_org(
                    **ghargs
                )
            else:
                log.info(
                    "Remove offline runner {owner}/{repo} {runner_id}".format(
                        **ghargs
                    )
                )
                self.ghapi.actions.delete_self_hosted_runner_from_repo(
                    **ghargs
                )

    @schedule.repeat(schedule.every(12).hours)
    def cleanup(self):
        " Run Github cleanup tasks "

        self.get_orgs()
        self.get_repos()

        # Only get User scope repos
        repos = [repo for repo in self.repos if repo.owner.type == "User"]

        args = []

        for org in self.orgs:
            args.append(dict(org=org.login))

        for repo in repos:
            args.append(dict(owner=repo.owner.login, repo=repo.name))

        for arg in args:
            self.cleanup_runners(arg)

    def queue_evt(self, evt):
        " Queue GH webhook event "

        if not frozenset(evt['labels']) in self.runnermap:
            log.warn(f"No matching config for labels {evt['labels']}")
            return
        evt['rc'] = self.runnermap.get(frozenset(evt['labels']))

        evt = dtypes.RunnerEvent(**evt)
        self.evtq.put((time.time(), evt))
        log.info(
            f"Queueing: job run id={evt.check_run_id} {evt.owner}/{evt.repo}"
        )

    def process_evt(self, evt: dtypes.RunnerEvent):
        " Process RunnerEvent"
        log.info(
            f"Processing: check_run id={evt.check_run_id} {evt.owner}/{evt.repo}"
        )

        evt.token = self.get_token(evt.dict()).token
        evt.pkg = self.get_runner_pkg(evt.rc)

        self.lxd.launch(evt)

    def runqueue(self):
        " Process event queue "
        while True:
            while len(self.lxd.get_workers()) >= cfg.max_workers:
                time.sleep(1)
            try:
                (ts, evt) = self.evtq.get()
                self.process_evt(evt)
            except Exception as e:
                log.error("Error processing queue")
                log.exception(e)

    def start_queue_task(self):
        " Start queue runner task "
        self.queuetask = util.threadit(self.runqueue, name="Queue")

    def start_web_task(self):
        " Start webhooks task "
        self.webtask = util.threadit(
            web.startserver, args=(self.queue_evt, ), name="Web"
        )

    def start_schedule_task(self):
        " Start scheduler task "
        self.schedtask = util.threadit(self.run_scheduler, name="Scheduler")

    def run_scheduler(self):
        " Run job scheduler "
        while True:
            schedule.run_pending()
            time.sleep(1)

    def startup_init(self):
        " Startup initilization "

        self.lxd.connect()
        self.update_pkg_cache()
        self.cleanup()
        self.submit_pending_runs()

        schedule.every().day.do(self.update_pkg_cache)
        schedule.every().day.do(self.cleanup)
