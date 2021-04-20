#!/usr/bin/env python3

import argparse
import sys

from .appconf import config as cfg
from .mngr import RunManager


def cliparse():
    parser = argparse.ArgumentParser(description='LXDRunner')
    default = cfg.__config__.default_files
    helptext = f"Configuration file. Default: {default}"
    parser.add_argument('-c', dest='cfgfile', help=helptext, default=None)
    args = parser.parse_args()
    return args


def main():

    args = cliparse()

    try:
        cfg.load(args.cfgfile)
    except FileNotFoundError:
        print(f"Config file does not exist: {args.cfgfile}")
        sys.exit(1)

    lxr = RunManager()
    lxr.lxd.connect()
    lxr.startup_init()

    lxr.start_web_task()
    lxr.start_queue_task()

    if sys.flags.interactive:
        print("Backgrounding scheduler, going interactive.")
        lxr.start_schedule_task()
    else:
        lxr.run_scheduler()

    return lxr


if __name__ == "__main__":
    lxr = main()
