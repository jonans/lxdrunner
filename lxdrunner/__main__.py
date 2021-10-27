#!/usr/bin/env python3

import argparse
import os
import pathlib
import sys
import logging

from lxdrunner import appconf

from .appconf import config as cfg
from .applog import log
from .mngr import RunManager
from . import __version__


def conf_list():
    files = [str(fname) for fname in appconf.def_configs]
    return f"[ {' | '.join(files) } ]"


def cliparse():
    parser = argparse.ArgumentParser(
        description=f'LXDRunner version {__version__}'
    )
    parser.prog = vars(sys.modules[__name__])['__package__']
    helptext = f"Configuration file. Default: { conf_list() }"
    parser.add_argument(
        '-c', dest='cfgfile', type=pathlib.Path, help=helptext, default=None
    )
    parser.add_argument(
        '-l',
        dest='loglevel',
        help='Log Level: %(default)s',
        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
        default=logging.getLevelName(log.level)
    )

    parser.add_argument(
        '-v',
        action='version',
        version='%(prog)s {version}'.format(version=__version__)
    )
    return parser


def main():

    parser = cliparse()
    args = parser.parse_args()

    if args.loglevel:
        log.setLevel(args.loglevel)

    if args.cfgfile:
        appconf.def_configs.clear()
        appconf.def_configs.append(args.cfgfile)

    if not cfg.config_exists():
        print(f"\nConfig file does not exist: { conf_list() }\n")
        parser.print_help()
        sys.exit(1)

    cfg.load()

    RunManager.configure()

    lxr = RunManager()
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
