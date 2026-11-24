"""Append-only JSON Lines file of guestbook messages, newest 20 kept in memory.

Each line is ``{"t": "<UTC ISO-8601, seconds, Z>", "m": "<text>"}``, appended
in send order. A blank or invalid line is skipped with one stderr warning that
names its line number. The file and its directory are never created by a read,
and the directory is never created at all.
"""

import collections
import datetime
import json
import os
import sys
import threading

LATEST = 20
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

Record = collections.namedtuple("Record", ("time", "text"))  # time: aware UTC datetime


def _decode(line):
    """Return the Record on one line, or None when the line is not one."""
    try:
        obj = json.loads(line)
    except ValueError:
        return None
    if not isinstance(obj, dict):
        return None
    stamp, text = obj.get("t"), obj.get("m")
    if not isinstance(stamp, str) or not isinstance(text, str):
        return None
    try:
        when = datetime.datetime.strptime(stamp, TIME_FORMAT)
    except ValueError:
        return None
    return Record(when.replace(tzinfo=datetime.timezone.utc), text)


class GuestbookStore:
    """The messages at ``path``; safe to share between request threads."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self._latest = None  # deque of Records, oldest first; None until loaded

    def _load(self):
        """Read the file once, keeping its last ``LATEST`` valid records.

        A missing file is empty; any other read error raises ``OSError``.
        """
        if self._latest is not None:
            return
        latest = collections.deque(maxlen=LATEST)
        try:
            fh = open(self.path, "r", encoding="utf-8", errors="replace", newline="\n")
        except FileNotFoundError:
            self._latest = latest
            return
        with fh:
            for lineno, line in enumerate(fh, start=1):
                record = _decode(line)
                if record is None:
                    print(f"guestbook: {self.path}: skipped invalid line {lineno}", file=sys.stderr, flush=True)
                else:
                    latest.append(record)
        self._latest = latest

    def latest(self):
        """Return the newest messages, newest first (at most ``LATEST``)."""
        with self._lock:
            self._load()
            return list(reversed(self._latest))

    def append(self, text, now=None):
        """Append one message durably and return its Record.

        Raises ``OSError`` when the file cannot be written; nothing is then
        added. A file that does not end in a newline gets one first.
        """
        when = (now or datetime.datetime.now(datetime.timezone.utc)).astimezone(datetime.timezone.utc)
        when = when.replace(microsecond=0)
        record = Record(when, text)
        line = json.dumps({"t": when.strftime(TIME_FORMAT), "m": text}, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            self._load()
            with open(self.path, "a+b") as fh:
                fh.seek(0, os.SEEK_END)
                prefix = b""
                if fh.tell() > 0:
                    fh.seek(-1, os.SEEK_END)
                    if fh.read(1) != b"\n":
                        prefix = b"\n"
                fh.write(prefix + line.encode("utf-8") + b"\n")
                fh.flush()
                os.fsync(fh.fileno())
            self._latest.append(record)
        return record
