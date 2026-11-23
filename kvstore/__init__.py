"""kvstore — a tiny append-only key-value store (standard library only)."""

from .log import (
    CorruptLogError,
    TornTailWarning,
    check_key,
    encode_record,
    replay,
)
from .store import KVStore

__all__ = [
    "CorruptLogError",
    "KVStore",
    "TornTailWarning",
    "check_key",
    "encode_record",
    "replay",
]
