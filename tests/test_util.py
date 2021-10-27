import secrets

from lxdrunner.appconf import config as cfg
import lxdrunner.util

#
# Test Data
#

from . import data

#
# Tests
#


class TestUtils:
    def test_make_name(self):
        name = lxdrunner.util.make_name()
        assert lxdrunner.util.has_prefix(name)

    def test_has_prefix(self):
        failname = secrets.token_urlsafe(20)
        assert lxdrunner.util.has_prefix(failname) is False
        goodname = f"{cfg.prefix}-123456789"
        assert lxdrunner.util.has_prefix(goodname)

    def test_env_str(self):
        env = {"KEY": "VALUE"}
        assert lxdrunner.util.env_str(env) == "KEY=VALUE\n"

    def test_image_to_source(self):
        image = "debian/11"
        source = lxdrunner.util.image_to_source(image)
        assert source['alias'] == image

        image = "ubuntu:focal"
        source = lxdrunner.util.image_to_source(image)
        assert source['protocol'] in ("simplestreams", "lxd")
        assert source['server'] == cfg.remotes["ubuntu"].addr
        assert source['alias'] == 'focal'
