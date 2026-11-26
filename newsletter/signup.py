"""Signup rules: a name of 1-80 code points and a well-formed email address.

Both rules run on the server, whatever the browser sent, and again in the
store, so invalid input is never written.
"""

import re

from guestbook.message import normalise as normalise_name

MAX_NAME = 80
MAX_EMAIL = 254

NAME_EMPTY = "name_empty"
NAME_TOO_LONG = "name_too_long"
EMAIL_EMPTY = "email_empty"
EMAIL_MALFORMED = "email_malformed"

# One "@", no whitespace, a non-empty local part and a domain of two or more
# non-empty dot-separated labels.
EMAIL_PATTERN = re.compile(r"[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+")


def address_key(email):
    """The duplicate key: the trimmed address, ``str.lower()`` (not casefold)."""
    return email.strip().lower()


def check(name_raw, email_raw):
    """Return ``(name, email, errors)`` for a submitted signup.

    ``name`` has its line breaks turned into spaces and is trimmed; ``email``
    is trimmed and keeps its case. ``errors`` maps ``"name"``/``"email"`` to an
    error code and is empty when the signup may be stored.
    """
    name = normalise_name(name_raw)
    email = email_raw.strip()
    errors = {}
    if not name:
        errors["name"] = NAME_EMPTY
    elif len(name) > MAX_NAME:
        errors["name"] = NAME_TOO_LONG
    if not email:
        errors["email"] = EMAIL_EMPTY
    elif len(email) > MAX_EMAIL or not EMAIL_PATTERN.fullmatch(email):
        errors["email"] = EMAIL_MALFORMED
    return name, email, errors
