import typing
import ipaddress
import pathlib
import importlib.resources
import urllib.parse
import threading

import xdg
from goodconf import GoodConf
from pydantic import BaseModel, IPvAnyAddress, constr, root_validator, validator

with importlib.resources.path('lxdrunner.scripts', 'setuprunner.sh') as path:
    def_script = path

appname = "lxdrunner"
def_config = xdg.xdg_config_home() / f"{appname}/config.yml"


class RunnerConf(BaseModel):
    name: str
    labels: frozenset
    image: str
    profiles: typing.List[str] = ['default']
    runner_os: typing.Literal['linux', 'win', 'osx']
    runner_arch: typing.Literal['x64', 'arm', 'arm64']
    type: typing.Literal['container', 'virtual-machine']
    setup_script: pathlib.Path = def_script
    max_workers: int = 10
    worksem: threading.BoundedSemaphore = None

    @validator('worksem', always=True)
    def set_worksemaphore(cls, v, *, values):
        out = threading.BoundedSemaphore(values['max_workers'])
        return out

    class Config:
        extra = 'allow'
        arbitrary_types_allowed = True


class Remote(BaseModel):
    protocol: typing.Literal['simplestreams', 'lxd']
    # Not yet available in stable pydantic
    # addr: stricturl(allowed_schemes=['http','https','unix'], host_required=False)
    addr: typing.Union[None, constr(regex=r"^((https|http)://|/)?")]

    # Workaround pyLXD <= v2.3.0 . File paths not recognized as http+unix://
    @validator('addr')
    def fix_unix_addr(cls, v):
        if v and v.startswith("/"):
            return "http+unix://{}".format(urllib.parse.quote(v), safe="")
        return v


def makepaths(confdir, cachedir):
    class DirPaths(BaseModel):
        pkgdir: pathlib.Path = cachedir / "pkgcache"
        servcerts: pathlib.Path = confdir / "servercerts"

    return DirPaths()


class AppConfig(GoodConf):
    "Configuration for My App"
    # GitHub
    pat: str
    hooksecret: str

    # Runner
    config_home: pathlib.Path = xdg.xdg_config_home() / appname
    cache_home: pathlib.Path = xdg.xdg_cache_home() / appname
    dirs: typing.Any = None

    @validator('dirs', pre=True, always=True)
    def default_dirs(cls, v, *, values, **kwargs):
        return makepaths(values['config_home'], values['cache_home'])

    prefix: str
    remotes: typing.Dict[str, Remote]
    runnermap: typing.List[RunnerConf]

    web_host: IPvAnyAddress = ipaddress.IPv4Address('0.0.0.0')
    web_port: int = 5000
    web_tls: bool = True

    cleanup: bool = True

    # For testing
    activecfg: typing.FrozenSet[str] = frozenset()
    max_workers: int
    def_repo_args: dict = {}
    def_org_args: dict = {}

    class Config:
        default_files = ["config.yml", def_config]
        file_env_var = "LXDRCFG"

    @root_validator
    def check_image_sources(cls, values):
        error = ""
        for rc in values.get('runnermap'):
            if ":" in rc.image:
                rem = rc.image.split(":")[0]
                if rem not in values.get("remotes"):
                    error += f"Remote '{rem}' is undefined\n"
        if error:
            raise ValueError(error)
        return values

    def key_pair_paths(self):
        return (
            self.config_home / "client.crt", self.config_home / "client.key"
        )

    def app_paths(self):
        return [self.config_home, self.cache_home
                ] + list(self.dirs.dict().values())


config = AppConfig(load=False)
