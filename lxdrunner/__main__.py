#!/usr/bin/env python3

import argparse
import sys

from .appconf import config as cfg
from .mngr import RunManager


def cliparse():
    parser = argparse.ArgumentParser(description='LXDRunner')
    parser.prog = vars(sys.modules[__name__])['__package__']
    defcfg = cfg.__config__.default_files
    defcfg = defcfg[0] if defcfg else "config.yml"
    helptext = f"Configuration file. Default: {defcfg}"
    parser.add_argument('-c', dest='cfgfile', help=helptext, default=defcfg)
    return parser


def main():

    parser = cliparse()
    args = parser.parse_args()

    try:
        cfg.load(args.cfgfile)
    except FileNotFoundError:
        print(f"\nConfig file does not exist: {args.cfgfile}\n")
        parser.print_help()
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
