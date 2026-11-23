"""Append-only JSON-lines log: record encoding, replay and crash recovery.

Each record is one UTF-8 line ending in ``\\n``::

    {"op":"set"|"del","k":<key>,"v":<value>,"exp":<number|null>,"crc":<int>}

``crc`` is ``zlib.crc32`` of the record *without* ``crc``, serialized
canonically (compact separators, sorted keys, ``ensure_ascii=False``, NaN
refused). Replay keeps the latest record per key; a ``del`` removes the key.

Recovery: an invalid *last* record is a torn write — it is dropped, the file
is truncated to where it starts and a :class:`TornTailWarning` names that
byte offset. An invalid *earlier* record is corruption — :class:`CorruptLogError`
names the file and 1-based line number, and the file is left untouched.
"""

import json
import math
import os
import warnings
import zlib

MAX_KEY_LENGTH = 128
RECORD_FIELDS = frozenset(("op", "k", "v", "exp", "crc"))
OPS = ("set", "del")


class CorruptLogError(Exception):
    """A record before the last one is invalid; the log is not usable.

    ``path`` and ``lineno`` (1-based) locate the bad record. ``store`` is the
    refused store instance when the error comes from opening a store.
    """

    def __init__(self, path, lineno, store=None):
        self.path = path
        self.lineno = lineno
        self.store = store
        super().__init__(f"corrupt log {path!r}: invalid record at line {lineno}")


class TornTailWarning(UserWarning):
    """The last record was torn (incomplete or invalid) and has been dropped."""


def check_key(key):
    """Raise ``ValueError`` naming the rule unless ``key`` is a valid key.

    A key is a ``str`` of 1-128 characters for which ``str.isprintable()``
    holds (spaces, Unicode and ``/`` pass; control, format characters and lone
    surrogates fail).
    """
    if not isinstance(key, str):
        raise ValueError(f"key length: key must be a str of 1-{MAX_KEY_LENGTH} characters, got {type(key).__name__}")
    if not 1 <= len(key) <= MAX_KEY_LENGTH:
        raise ValueError(f"key length: key must be 1-{MAX_KEY_LENGTH} characters, got {len(key)}")
    if not key.isprintable():
        raise ValueError("key printable: key must contain only printable characters")


def canonical_json(obj):
    """Serialize ``obj`` the canonical way; raises ``ValueError``/``TypeError``."""
    return json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=False, allow_nan=False)


def record_crc(record):
    """CRC32 of ``record`` (a dict without ``crc``) in canonical form."""
    return zlib.crc32(canonical_json(record).encode("utf-8"))


def encode_record(op, k, v=None, exp=None):
    """Return one log line (bytes, ending in ``\\n``) for the record."""
    record = {"op": op, "k": k, "v": v, "exp": exp}
    record["crc"] = record_crc(record)
    return (canonical_json(record) + "\n").encode("utf-8")


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def decode_record(raw):
    """Parse one line (bytes without ``\\n``); return the record dict or None if invalid."""
    try:
        record = json.loads(raw.decode("utf-8"))
    except ValueError:  # covers UnicodeDecodeError and JSONDecodeError
        return None
    if not isinstance(record, dict) or set(record) != RECORD_FIELDS:
        return None
    op, k, exp, crc = record["op"], record["k"], record["exp"], record["crc"]
    if op not in OPS:
        return None
    try:
        check_key(k)
    except ValueError:
        return None
    if exp is not None and not (_is_number(exp) and math.isfinite(exp)):
        return None
    if op == "del" and (record["v"] is not None or exp is not None):
        return None
    if not isinstance(crc, int) or isinstance(crc, bool):
        return None
    body = {name: record[name] for name in ("op", "k", "v", "exp")}
    try:
        if record_crc(body) != crc:
            return None
    except (ValueError, TypeError):  # NaN/Infinity or unencodable text
        return None
    return record


class ReplayResult:
    """What replay found: the live index and the shape of the log."""

    def __init__(self, index, records, missing_newline):
        #: key -> (value, exp); exp is an absolute time or None. Expired
        #: entries are kept; the store decides expiry against its clock.
        self.index = index
        #: number of valid records left in the log (sets and dels).
        self.records = records
        #: True when the last kept record has no trailing ``\\n``.
        self.missing_newline = missing_newline


def replay(path):
    """Replay the log at ``path`` (creating it empty if missing).

    Returns a :class:`ReplayResult`. Truncates a torn last record with a
    :class:`TornTailWarning`; raises :class:`CorruptLogError` without touching
    the file if any earlier record is invalid.
    """
    path = os.fspath(path)
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except FileNotFoundError:
        with open(path, "ab"):
            pass
        data = b""

    # Split into (start offset, raw line) pairs. A final empty piece after a
    # trailing "\n" is not a record.
    lines = []
    offset = 0
    pieces = data.split(b"\n")
    for i, piece in enumerate(pieces):
        if i == len(pieces) - 1 and piece == b"":
            break
        lines.append((offset, piece))
        offset += len(piece) + 1

    records = [decode_record(raw) for _, raw in lines]
    for lineno, record in enumerate(records[:-1], start=1):
        if record is None:
            raise CorruptLogError(path, lineno)

    if records and records[-1] is None:
        torn_at = lines[-1][0]
        with open(path, "r+b") as fh:
            fh.truncate(torn_at)
            fh.flush()
            os.fsync(fh.fileno())
        warnings.warn(
            TornTailWarning(f"log {path!r}: dropped torn last record; truncated to byte offset {torn_at}"),
            stacklevel=2,
        )
        records.pop()
        lines.pop()
        missing_newline = False
    else:
        missing_newline = bool(data) and not data.endswith(b"\n")

    index = {}
    for record in records:
        if record["op"] == "set":
            index[record["k"]] = (record["v"], record["exp"])
        else:
            index.pop(record["k"], None)
    return ReplayResult(index, len(records), missing_newline)
