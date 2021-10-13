import unittest.mock as mock

import pytest
from pydantic import BaseModel
import pylxd.exceptions

from lxdrunner.appconf import config as cfg
from lxdrunner import util
import lxdrunner.lxd
from lxdrunner.dtypes import RunnerEvent
from lxdrunner.appconf import RunnerConf

#
# Test Data
#


class FakeLXDInstance(BaseModel):
    name: str


non_workers = [FakeLXDInstance(name=x) for x in range(3)]
lxd_workers = [FakeLXDInstance(name=util.make_name()) for x in range(5)]

goodrc = RunnerConf(
    name="Test Runner Conf",
    labels=['self-hosted', 'linux'],
    image="ubuntu/latest",
    profiles=['default'],
    runner_os='linux',
    runner_arch='x64',
    type='container'
)

evt = RunnerEvent(owner='owner', repo='repo', org='testorg', rc=goodrc)


@pytest.fixture
def lxdm():
    lxd = lxdrunner.lxd.LXDRunner(connect=False)
    with mock.patch.object(lxd, 'client'):
        yield lxd


def test_push_file(lxdm):
    instance = mock.Mock()
    lxdm.pushfile("/dev/null", instance, "/root/file", mode="0600")
    instance.files.put.assert_called_with("/root/file", b'', mode="0600")


def test_get_workers(lxdm):
    lxdm.client.instances.all.return_value = lxd_workers + non_workers
    workers = lxdm.get_workers()
    assert lxdm.client.instances.all.called
    assert workers == lxd_workers


def test_verify_launch(lxdm):
    assert lxdm.verify_launch(evt)


def test_verify_launch_missing_image(lxdm):
    lxdm.client.images.get_by_alias.side_effect = pylxd.exceptions.NotFound(
        'missing'
    )
    assert lxdm.verify_launch(evt) is False


def test_verify_launch_missing_profile(lxdm):
    lxdm.client.profiles.exists.return_value = False
    assert lxdm.verify_launch(evt) is False


def test_launch_instance(lxdm):
    instname = util.make_name()
    expected_cfg = dict(
        name=instname,
        ephemeral=True,
        profiles=goodrc.profiles,
        source=dict(type="image", alias=goodrc.image, mode="pull"),
        type=goodrc.type
    )
    lxdm.launch_instance(instname, goodrc)
    assert lxdm.client.instances.create.called
    called_cfg = lxdm.client.instances.create.call_args.args[0]
    assert called_cfg == expected_cfg


def test__launch(lxdm):

    lxdm.start_gha_runner = mock.Mock()
    assert lxdm._launch(evt) is True, "Launch should succeed"

    lxdm.start_gha_runner.reset_mock()
    lxdm.start_gha_runner.side_effect = Exception("Random exception")
    lxdm._cleanup_instance = mock.Mock()
    assert lxdm._launch(evt) is False, "Launch should have failed"
    assert lxdm._cleanup_instance.called, "Cleanup should have been called"


def test__cleanup_instance(lxdm):
    assert lxdm._cleanup_instance(
        "randomname"
    ) is True, "Inst should be stopped, deleted"

    lxdm.client.instances.get.side_effect = pylxd.exceptions.LXDAPIException(
        "LXD Failure"
    )
    assert lxdm._cleanup_instance(
        "randomname"
    ) is False, "LXD lookup should have failed"
