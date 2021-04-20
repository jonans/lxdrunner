import datetime
import dataclasses

from lxdrunner.appconf import config as cfg
import lxdrunner.dtypes as dtypes
#
# Test Data
#

org_args = dict(org="testorg", target="testorg")
repo_args = dict(
    owner="testowner", repo="testrepo", target="testowner/testrepo"
)

now = datetime.datetime.now().astimezone()


@dataclasses.dataclass
class Token:
    token: str = 'FAKE_TOKEN'
    expires_at: str = (now + datetime.timedelta(minutes=60)).isoformat()


valid_token = Token()
expired_token = Token(expires_at=now.isoformat())


@dataclasses.dataclass
class Package:
    os: str
    architecture: str
    download_url: str
    filename: str
    linkname: str


pkg0 = dtypes.RunnerPackage(
    os='osx',
    architecture='x64',
    download_url='https://localhost/actions-runner-osx-x64-2.277.1.tar.gz',
    filename='actions-runner-osx-x64-2.277.1.tar.gz',
    linkname='actions-runner-osx-x64-latest'
)
pkg0_expected_linkname = "actions-runner-osx-x64-latest"

pkg1 = dtypes.RunnerPackage(
    os='linux',
    architecture='arm',
    download_url='https://localhost/actions-runner-linux-arm-2.277.1.tar.gz',
    filename='actions-runner-linux-arm-2.277.1.tar.gz',
    linkname='actions-runner-linux-arm-latest'
)
pkg1_expected_linkname = "actions-runner-linux-arm-latest"

pkgs = (pkg0, pkg1)
