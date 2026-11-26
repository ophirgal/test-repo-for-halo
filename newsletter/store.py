"""Append-only JSON Lines file of newsletter signups, one per address.

Each line is ``{"t": "<UTC ISO-8601, seconds, Z>", "n": "<name>", "e": "<email>"}``,
appended oldest first. A blank or invalid line is skipped with one stderr
warning that names its line number. The file and its directory are never
created by a read, and the directory is never created at all.

One lock covers the duplicate check and the append, so one server process
stores an address once however many requests race. Several processes on one
file are not supported.
"""

import collections
import datetime
import json
import os
import sys
import threading

from .signup import address_key, check

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

Record = collections.namedtuple("Record", ("time", "name", "email"))  # time: aware UTC datetime


def _decode(line):
    """Return the Record on one line, or None when the line is not one."""
    try:
        obj = json.loads(line)
    except ValueError:
        return None
    if not isinstance(obj, dict):
        return None
    stamp, name, email = obj.get("t"), obj.get("n"), obj.get("e")
    if not all(isinstance(v, str) for v in (stamp, name, email)):
        return None
    try:
        when = datetime.datetime.strptime(stamp, TIME_FORMAT)
    except ValueError:
        return None
    return Record(when.replace(tzinfo=datetime.timezone.utc), name, email)


def read_records(path):
    """Yield every valid record in ``path``, oldest first.

    A missing file yields nothing; any other read error raises ``OSError``.
    """
    try:
        fh = open(path, "r", encoding="utf-8", errors="replace", newline="\n")
    except FileNotFoundError:
        return
    with fh:
        for lineno, line in enumerate(fh, start=1):
            record = _decode(line)
            if record is None:
                print(f"newsletter: {path}: skipped invalid line {lineno}", file=sys.stderr, flush=True)
            else:
                yield record


class SignupStore:
    """The signups at ``path``; safe to share between request threads."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self._keys = None  # set of address keys; None until loaded

    def _load(self):
        if self._keys is None:
            self._keys = {address_key(r.email) for r in read_records(self.path)}

    def records(self):
        """Return every stored signup, oldest first."""
        return list(read_records(self.path))

    def add(self, name, email, now=None):
        """Store a signup once per address; return True if it was new.

        Raises ``ValueError`` for an invalid name or email (nothing is
        written) and ``OSError`` when the file cannot be read or written
        (nothing is then remembered). A known address stores nothing and
        leaves the first record unchanged.
        """
        name, email, errors = check(name, email)
        if errors:
            raise ValueError(f"invalid signup: {sorted(errors.values())}")
        key = address_key(email)
        when = (now or datetime.datetime.now(datetime.timezone.utc)).astimezone(datetime.timezone.utc)
        stamp = when.replace(microsecond=0).strftime(TIME_FORMAT)
        line = json.dumps({"t": stamp, "n": name, "e": email}, ensure_ascii=False, separators=(",", ":"))
        with self._lock:
            self._load()
            if key in self._keys:
                return False
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
            self._keys.add(key)
        return True
