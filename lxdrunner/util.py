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


def threadit(func, **kwargs):
    thread = threading.Thread(target=func, daemon=True, **kwargs)
    thread.start()
    return thread


def env_str(data):

    sdata = ""
    for key, val in data.items():
        sdata += f"{key}={val}\n"
    return sdata


def image_to_source(image):
    " Convert image resource [<remote>:]<image>  to source object "
    alias = image
    source = dict(type="image", mode="pull")

    if ":" in image:
        remote_name, alias = image.split(":", 1)
        remote = cfg.remotes.get(remote_name)
        source['protocol'] = remote.protocol
        source['server'] = remote.addr

    source['alias'] = alias
    return source
