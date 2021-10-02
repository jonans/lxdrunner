#!/usr/bin/env python3

import hmac

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
        log.info(f"- HMAC: { mac }")
        log.info(f"- GHSIG: { sig }")
    return result


@app.route("/hooks/lxdrunner", methods=["POST", "GET"])
def githubhook():
    ghevt = request.headers.get("X-GitHub-Event")

    if not ghevt:
        log.warning("Not a Github webhook event")
        return "UNAUTHORIZED", 401

    if not validate_webhook():
        return "UNAUTHORIZED", 401

    data = request.json

    # Event should be check_run, app == actions and status == queued
    if (
        ghevt != "workflow_job"
        or data.get("workflow_job").get("status") != "queued"
    ):

        log.info(f"Skipping event: {ghevt} , action={data['action']}")
        return "Skipping Event"

    gh = dict(
        check_run_id=data.get("workflow_job", {}).get("id"),
        repo=data.get("repository", {}).get("name"),
        owner=data.get("repository", {}).get("owner", {}).get("login"),
        org=data.get("organization", {}).get("login"),
        labels=data.get("workflow_job", {}).get("labels")
    )
    log.info(f"Accepted event: {ghevt} , action={data['action']}")
    app.queue_evt(gh)
    return "OK"


def startserver(queue_evt):
    app.queue_evt = queue_evt
    tls = 'adhoc' if cfg.web_tls else None
    app.run(host=str(cfg.web_host), port=cfg.web_port, ssl_context=tls)
