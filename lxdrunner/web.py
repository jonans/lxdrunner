#!/usr/bin/env python3

import hmac
import logging

from flask import Flask
from flask import request

from .appconf import config as cfg
from .applog import log

app = Flask("LXDrun")


def validate_webhook():
    " Validate Github webhook signature "

    evt = request.headers.get("X-GitHub-Event")
    failmsg = f"Webhook HMAC failed {evt}"
    sig = request.headers.get("X-Hub-Signature-256")

    if not sig:
        log.warning(failmsg + "missing X-Hub-Signature-256")
        return False

    mac = "sha256=" + hmac.new(
        cfg.hooksecret.encode('utf8'), request.data, "sha256"
    ).hexdigest()

    result = hmac.compare_digest(mac, sig)
    if not result:
        log.warning(failmsg)
        log.debug(f"- HMAC: { mac }")
        log.debug(f"- GHSIG: { sig }")
    return result


@app.route("/hooks/lxdrunner", methods=["POST", "GET"])
def githubhook():
    ghevt = request.headers.get("X-GitHub-Event")

    if not ghevt:
        log.debug("Not a Github webhook event")
        return "UNAUTHORIZED", 401

    if not validate_webhook():
        return "UNAUTHORIZED", 401

    data = request.json

    job = data.get("workflow_job", {})
    # Event should be workflow_job, status == queued, self-hosted
    if (
        ghevt != "workflow_job" or job.get("status") != "queued"
        or "self-hosted" not in job.get("labels")
    ):

        log.debug(f"Skipping event: {ghevt} , action={data['action']}")
        return "Skipping Event"

    gh = dict(
        check_run_id=job.get("id"),
        repo=data.get("repository", {}).get("name"),
        owner=data.get("repository", {}).get("owner", {}).get("login"),
        org=data.get("organization", {}).get("login"),
        labels=job.get("labels")
    )
    log.info(f"Accepted event: {ghevt} , action={data['action']}")
    app.queue_evt(gh)
    return "OK"


def startserver(queue_evt):
    app.queue_evt = queue_evt
    #app.logger.setLevel(logging.WARN)
    tls = 'adhoc' if cfg.web_tls else None
    app.run(host=str(cfg.web_host), port=cfg.web_port, ssl_context=tls)
