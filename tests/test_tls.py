from unittest import mock
import pytest
import os

import lxdrunner.appconf
from lxdrunner.appconf import config as cfg

import lxdrunner.tls
#
# Tests
#


@pytest.fixture
def certfiles():
    with mock.patch(
        'lxdrunner.appconf.AppConfig.key_pair_paths',
        return_value=(mock.MagicMock(), mock.MagicMock())
    ):
        yield cfg.key_pair_paths()


class TestTLS:

    #@mock.patch('lxdrunner.tls.Path')
    def test_gen_key_pair(self, certfiles):
        mPath = certfiles[0]
        lxdrunner.tls.gen_key_pair()
        print("CALLS", mPath.mock_calls)
        assert mPath.exists.call_count == 1
        assert mPath.open.call_count == 0, "keys exist, should not be written"
        mPath.exists.return_value = False
        lxdrunner.tls.gen_key_pair()
        assert mPath.open.call_count == 1, "open key file not called"
        assert certfiles[1].open.call_count == 1, "open crt file not called"
