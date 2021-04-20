import logging

logging.basicConfig()
log = logging.getLogger("LXDrun")
log.propagate = False
log.setLevel(logging.INFO)

logfmt = logging.Formatter('%(threadName)s: %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(logfmt)

log.addHandler(handler)
