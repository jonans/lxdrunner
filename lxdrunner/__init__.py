from importlib.metadata import version

try:
    __version__ = version('lxdrunner')
except:
    __version__ = "0.0.0"
