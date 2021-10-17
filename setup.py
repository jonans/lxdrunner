import setuptools

# Work around for https://github.com/pypa/pip/issues/7953
import site
import sys

site.ENABLE_USER_SITE = "--user" in sys.argv[1:]

setuptools.setup()
