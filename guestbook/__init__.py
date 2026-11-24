"""guestbook — the /guestbook page's rules, file store and rendering (SCRUM-126).

Standard library only. No HTTP knowledge: ``serve.py`` does the routing.
"""

from .message import EMPTY, MAX_LEN, TOO_LONG, check, normalise
from .page import render
from .store import LATEST, GuestbookStore, Record

__all__ = [
    "EMPTY",
    "LATEST",
    "MAX_LEN",
    "TOO_LONG",
    "GuestbookStore",
    "Record",
    "check",
    "normalise",
    "render",
]
