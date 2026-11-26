"""newsletter — signup rules, the signup file and its CSV export (SCRUM-103).

Standard library only. No HTTP knowledge: ``serve.py`` does the routing.
The export command lives in ``newsletter.export`` (``python3 -m newsletter export``).
"""

from .signup import (
    EMAIL_EMPTY,
    EMAIL_MALFORMED,
    MAX_EMAIL,
    MAX_NAME,
    NAME_EMPTY,
    NAME_TOO_LONG,
    address_key,
    check,
)
from .store import Record, SignupStore

__all__ = [
    "EMAIL_EMPTY",
    "EMAIL_MALFORMED",
    "MAX_EMAIL",
    "MAX_NAME",
    "NAME_EMPTY",
    "NAME_TOO_LONG",
    "Record",
    "SignupStore",
    "address_key",
    "check",
]
