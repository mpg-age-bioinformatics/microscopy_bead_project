import logging

# Shared logging setup for all entry-point scripts.
#
# Logs go to stdout only, which is captured per-container by `docker logs`.
# We intentionally do NOT write a log file into the mounted volume: that path
# can be shared by multiple users/containers, and concurrent writers would
# interleave or corrupt a shared file. `docker logs` keeps each run isolated.

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level=logging.INFO):
    """Configure the root logger once. Safe to call from multiple scripts.

    Returns the root logger. If logging is already configured (handlers
    present), it is left untouched so importing modules can't clobber it.
    """
    root = logging.getLogger()
    if root.handlers:
        return root

    root.setLevel(level)
    formatter = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    return root
