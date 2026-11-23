"""Atomic log replacement for compaction, and stale temp-file clean-up.

The compacted records are written to ``<log path>.compact.tmp`` in the same
directory, flushed and fsynced, then ``os.replace``d over the log, then the
directory is fsynced (POSIX). A crash before the rename leaves the original
log intact; the stale temp file is removed the next time the store opens.
"""

import os

TEMP_SUFFIX = ".compact.tmp"


def temp_path(path):
    return os.fspath(path) + TEMP_SUFFIX


def remove_stale_temp(path):
    """Delete a temp file left by a compaction that never reached its rename."""
    try:
        os.remove(temp_path(path))
    except FileNotFoundError:
        pass


def _fsync_dir(directory):
    if os.name == "nt":  # directories cannot be opened for fsync on Windows
        return
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_and_swap(path, lines):
    """Atomically replace the log at ``path`` with ``lines`` (encoded records)."""
    path = os.fspath(path)
    tmp = temp_path(path)
    with open(tmp, "wb") as fh:
        for line in lines:
            fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    _fsync_dir(os.path.dirname(os.path.abspath(path)))
