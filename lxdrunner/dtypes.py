#!/usr/bin/env python3

import typing

from pydantic import BaseModel, validator

from .appconf import RunnerConf


def maketarget(ghargs):
    "Return target scope for GitHub depending if request is org or repo"
    return ghargs.get("org") or "/".join(
        (ghargs.get("owner"), ghargs.get("repo"))
    )


class RunnerPackage(BaseModel):
    os: str
    architecture: str
    download_url: str
    filename: str
    linkname: str


class RunnerEvent(BaseModel):
    owner: str
    repo: str
    org: str
    target: str = ''
    target_url: str = 'https://github.com/'
    rc: RunnerConf
    pkg: typing.Any
    token: str = ""
    check_run_id: str = ""

    @validator('target', always=True)
    def compute_target(cls, v, values, field, **kwargs):
        return maketarget(values)

    @validator('target_url', always=True)
    def compute_target_url(v, values):
        return v + values['target']
