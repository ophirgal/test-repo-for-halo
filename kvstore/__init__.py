"""kvstore — a tiny append-only key-value store (standard library only)."""

from .log import (
    CorruptLogError,
    TornTailWarning,
    check_key,
    encode_record,
    replay,
)

__all__ = [
    "CorruptLogError",
    "TornTailWarning",
    "check_key",
    "encode_record",
    "replay",
]
