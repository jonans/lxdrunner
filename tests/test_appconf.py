from unittest import mock
from pathlib import Path
import lxdrunner.appconf as appconf

cfg = appconf.config

#
# Tests
#


class TestAppConf:
    def test_key_pair_paths(self):
        (p1, p2) = cfg.key_pair_paths()
        assert p1.with_name("client.crt")
        assert p2.with_name("client.key")
