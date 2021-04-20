import unittest.mock as mock
import pytest
import dataclasses
import os
from pathlib import Path

from lxdrunner.appconf import config as cfg

import lxdrunner.mngr

#
# Test Data
#

from . import data
from fastcore.foundation import L


@dataclasses.dataclass
class GHReleaseAsset:
    name: str
    browser_download_url: str


@dataclasses.dataclass
class GHRelease:
    prerelease: bool
    assets: list


asset = GHReleaseAsset(
    name='actions-runner-osx-x64-2.277.1.tar.gz',
    browser_download_url=
    "https://localhost/actions-runner-osx-x64-2.277.1.tar.gz"
)

ghrels = L(
    GHRelease(prerelease=True, assets=[asset]),
    GHRelease(prerelease=False, assets=[asset])
)

#
# Tests
#


@pytest.fixture
def mngr():
    " Return RunManager() object with mocked GHAPI "
    mn = lxdrunner.mngr.RunManager()
    with mock.patch.object(mn, 'ghapi'):
        yield mn


def test_get_token_doesnt_exist(mngr):
    mngr.get_token(data.org_args)
    assert mngr.ghapi.actions.create_registration_token_for_org.called
    mngr.ghapi.reset_mock()
    mngr.get_token(data.repo_args)
    assert mngr.ghapi.actions.create_registration_token_for_repo.called


def test_get_token_valid(mngr):
    mngr.reg_tokens = {data.org_args['org']: data.valid_token}
    mngr.get_token(data.org_args)
    assert not mngr.ghapi.actions.create_registration_token_for_org.called


def test_get_token_expired(mngr):
    mngr.reg_tokens = {data.org_args['org']: data.expired_token}
    mngr.get_token(data.org_args)
    assert mngr.ghapi.actions.create_registration_token_for_org.called


def test_get_runners(mngr):
    mngr.get_runners(data.repo_args)
    assert mngr.ghapi.actions.list_self_hosted_runners_for_repo.called

    mngr.ghapi.reset_mock()

    mngr.get_runners(data.org_args)
    assert mngr.ghapi.actions.list_self_hosted_runners_for_org.called


def test_get_packages(mngr):
    mngr.ghapi.repos.list_releases.return_value = ghrels
    mngr.get_packages()
    assert mngr.ghapi.repos.list_releases.called
    assert len(mngr.pkgs) == 1, "Pre-release not filtered"
    assert mngr.pkgs[0].filename == asset.name
    assert mngr.pkgs[0].download_url == asset.browser_download_url
    assert mngr.pkgs[0].linkname[:-6] in asset.name, "pkg.linkname incorrect"


def touchfile(url, fname):
    Path(fname).touch()


@mock.patch('urllib.request.urlretrieve', side_effect=touchfile)
def test_update_pkg_cache(m_url, mngr, tmpdir):
    # Inject list of packages
    mngr.get_packages = mock.Mock()
    mngr.pkgs = data.pkgs

    os.chdir(tmpdir)
    pkgdir = Path(cfg.pkgdir)
    pkg_cnt = len(data.pkgs)

    mngr.update_pkg_cache()
    # Files will be downloaded
    assert m_url.call_count == pkg_cnt, "Download count != pkg count"
    # pkgs * 2 files created
    assert len(
        list(pkgdir.iterdir())
    ) == pkg_cnt * 2, "File count != 2*pkg count"

    m_url.reset_mock()

    fp = Path(cfg.pkgdir + "/extra_file")
    fp.touch()
    assert fp.exists(), "extra_file is not present"

    mngr.update_pkg_cache()
    # Files exist, no downloaded
    assert m_url.call_count == 0, "No files should be downloaded"
    assert not fp.exists(), "extra_file should not exist"
