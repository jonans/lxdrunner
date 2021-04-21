#!/usr/bin/env python3

import secrets
import threading

from .appconf import config as cfg
#
# Helper Functions
#


def has_prefix(name):
    " Check if name is managed by LXDRunner "
    return name.startswith(cfg.prefix + "-")


def make_name():
    " Generate name based on prefix and random token "

    return "{}-{}".format(cfg.prefix, secrets.token_hex(3))


def linkname(pkg):
    " Add linkname to pkg "
    pkg.linkname = "-".join(pkg.filename.split('-')[:4] + ['latest'])
    return pkg


def threadit(func, **kwargs):
    thread = threading.Thread(target=func, daemon=True, **kwargs)
    thread.start()
    return thread


def env_str(data):

    sdata = ""
    for key, val in data.items():
        sdata += f"{key}={val}\n"
    return sdata
