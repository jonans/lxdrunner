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

    def disabled_linkname(self):
        pkg = lxdrunner.util.linkname(data.pkg0)
        assert pkg.linkname == data.pkg0.expected_linkname
