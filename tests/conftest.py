import os


def pytest_configure(config):
    print("Setting up test config file ")
    os.environ['LXDRCFG'] = "tests/config.yml"
    from lxdrunner.appconf import config as cfg
    cfg.load("tests/config.yml")
