import typing
import ipaddress
import pathlib
import importlib.resources

from goodconf import GoodConf
from pydantic import BaseModel, IPvAnyAddress

with importlib.resources.path('lxdrunner.scripts', 'setuprunner.sh') as path:
    def_script = path


class RunnerConf(BaseModel):
    name: str
    labels: frozenset
    image: str
    profiles: typing.List[str] = ['default']
    runner_os: typing.Literal['linux', 'win', 'osx']
    runner_arch: typing.Literal['x64', 'arm', 'arm64']
    type: typing.Literal['container', 'virtual-machine']
    setup_script: pathlib.Path = def_script

    class Config:
        extra = 'allow'


class AppConfig(GoodConf):
    "Configuration for My App"
    # GitHub
    pat: str
    hooksecret: str
    # LXD
    socket: str
    pkgdir: str
    # Runner
    prefix: str
    setupscript: str
    runnermap: typing.List[RunnerConf]
    # For testing
    activecfg: typing.FrozenSet[str] = frozenset()
    rundelay: int
    max_workers: int
    # Testing
    def_repo_args: dict = {}
    def_org_args: dict = {}
    # Web
    web_host: IPvAnyAddress = ipaddress.IPv4Address('0.0.0.0')
    web_port: int = 5000
    web_tls: bool = True

    cleanup: bool = True

    class Config:
        default_files = ["config.yml"]
        file_env_var = "LXDRCFG"


config = AppConfig(load=False)
