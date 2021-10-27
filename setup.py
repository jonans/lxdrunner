#!/usr/bin/env python3

import setuptools

# Work around for https://github.com/pypa/pip/issues/7953
import site
import sys

site.ENABLE_USER_SITE = "--user" in sys.argv[1:]

version_config = {
    "dev_template": "{tag}.dev{ccount}+{branch}.{sha}",
    "dirty_template": "{tag}.dev{ccount}+{branch}.{sha}",
}

setuptools.setup(version_config=version_config, )
