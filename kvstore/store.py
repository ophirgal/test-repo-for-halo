"""The public key-value store: dict-like API with per-key TTL.

Every operation runs under one lock per store. Each mutation is validated,
appended, flushed and fsynced before it returns. Time comes from an injected
``clock`` (default ``time.time``) so tests never sleep.

Compaction rewrites the log to one ``set`` per live, unexpired key. It runs
on ``compact()`` and automatically after a mutation once live keys are
under half of the log's records.
"""

import math
import os
import threading
import time
import warnings

from . import compaction
from .log import CorruptLogError, canonical_json, check_key, encode_record, replay

MAX_VALUE_BYTES = 65536
#: Compact automatically when live keys / log records falls strictly below this.
AUTO_COMPACT_RATIO = 0.5


def check_value(value):
    """Raise ``ValueError`` naming the rule unless ``value`` is a storable JSON value."""
    try:
        size = len(canonical_json(value).encode("utf-8"))
    except (TypeError, ValueError) as err:  # non-JSON types, NaN/Infinity, lone surrogates
        raise ValueError(f"value JSON: value must be a JSON value ({err})") from None
    if size > MAX_VALUE_BYTES:
        raise ValueError(f"value size: serialized value is {size} bytes, at most {MAX_VALUE_BYTES} allowed")


def check_ttl(ttl):
    """Raise ``ValueError`` unless ``ttl`` is None or a finite number of seconds > 0."""
    if ttl is None:
        return
    if isinstance(ttl, bool) or not isinstance(ttl, (int, float)):
        raise ValueError(f"ttl: ttl must be a number of seconds, got {type(ttl).__name__}")
    try:
        finite = math.isfinite(ttl)
    except OverflowError:
        finite = False
    if not finite or ttl <= 0:
        raise ValueError(f"ttl: ttl must be finite and greater than 0, got {ttl!r}")


class KVStore:
    """A file-backed key-value store over one append-only log.

    ``KVStore(path, clock=time.time)``. Opening over a log corrupt in the
    middle raises :class:`CorruptLogError`; the refused instance is
    ``err.store`` and raises ``CorruptLogError`` on every operation.
    """

    def __init__(self, path, *, clock=time.time):
        self.path = os.fspath(path)
        self._clock = clock
        self._lock = threading.Lock()
        self._fh = None
        self._refused = None
        self._closed = False
        compaction.remove_stale_temp(self.path)
        try:
            result = replay(self.path)
        except CorruptLogError as err:
            err.store = self
            self._refused = err
            raise
        self._index = result.index
        self._records = result.records
        self._needs_newline = result.missing_newline
        self._fh = open(self.path, "ab")

    # -- lifecycle -------------------------------------------------------

    def close(self):
        with self._lock:
            self._closed = True
            if self._fh is not None:
                self._fh.close()
                self._fh = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- internals (call with the lock held) -----------------------------

    def _check_usable(self):
        if self._refused is not None:
            err = self._refused
            raise CorruptLogError(err.path, err.lineno, store=self)
        if self._closed:
            raise ValueError("store is closed")

    def _live(self, key, now):
        entry = self._index.get(key)
        if entry is None:
            return None
        if entry[1] is not None and entry[1] <= now:
            return None
        return entry

    def _append(self, line):
        if self._needs_newline:
            line = b"\n" + line
        self._fh.write(line)
        self._fh.flush()
        os.fsync(self._fh.fileno())
        self._needs_newline = False
        self._records += 1

    def _compact_locked(self):
        now = self._clock()
        live = {k: e for k, e in self._index.items() if e[1] is None or e[1] > now}
        lines = [encode_record("set", k, v, exp) for k, (v, exp) in sorted(live.items())]
        try:
            compaction.write_and_swap(self.path, lines)
        finally:
            # Once the rename has happened, appends must go to the new file,
            # even if a later step (the directory fsync) failed.
            if os.fstat(self._fh.fileno()).st_ino != os.stat(self.path).st_ino:
                self._fh.close()
                self._fh = open(self.path, "ab")
                self._index = live
                self._records = len(lines)
                self._needs_newline = False

    def _after_mutation(self):
        """Compact automatically once live keys are under half of the log's records."""
        now = self._clock()
        live = sum(1 for _, exp in self._index.values() if exp is None or exp > now)
        if self._records and live / self._records < AUTO_COMPACT_RATIO:
            try:
                self._compact_locked()
            except OSError as err:
                # The mutation itself is already durable; report, don't fail it.
                warnings.warn(f"automatic compaction of {self.path!r} failed: {err}", RuntimeWarning, stacklevel=3)

    # -- public API ------------------------------------------------------

    def set(self, k, v, ttl=None):
        """Store ``v`` under ``k``; with ``ttl`` it expires ``ttl`` seconds from now."""
        with self._lock:
            self._check_usable()
            check_key(k)
            check_value(v)
            check_ttl(ttl)
            exp = None if ttl is None else self._clock() + ttl
            self._append(encode_record("set", k, v, exp))
            self._index[k] = (v, exp)
            self._after_mutation()

    def get(self, k):
        """Return the value of a live key; ``KeyError`` if missing or expired."""
        with self._lock:
            self._check_usable()
            check_key(k)
            entry = self._live(k, self._clock())
            if entry is None:
                raise KeyError(k)
            return entry[0]

    def delete(self, k):
        """Delete a live key; ``KeyError`` (and nothing appended) if missing or expired."""
        with self._lock:
            self._check_usable()
            check_key(k)
            if self._live(k, self._clock()) is None:
                raise KeyError(k)
            self._append(encode_record("del", k))
            del self._index[k]
            self._after_mutation()

    def keys(self):
        """Return the live, unexpired keys sorted ascending."""
        with self._lock:
            self._check_usable()
            now = self._clock()
            return sorted(k for k in self._index if self._live(k, now) is not None)

    def compact(self):
        """Rewrite the log atomically to hold only live, unexpired records."""
        with self._lock:
            self._check_usable()
            self._compact_locked()
