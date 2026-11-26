"""newsletter — signup rules, the signup file, its CSV export and the journey pages (SCRUM-103).

Standard library only. No HTTP knowledge: ``serve.py`` does the routing.
The export command lives in ``newsletter.export`` (``python3 -m newsletter export``).
"""

from .pages import FORM_JS, render_form, render_thanks, render_welcome
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
    "FORM_JS",
    "EMAIL_MALFORMED",
    "MAX_EMAIL",
    "MAX_NAME",
    "NAME_EMPTY",
    "NAME_TOO_LONG",
    "Record",
    "SignupStore",
    "address_key",
    "check",
    "render_form",
    "render_thanks",
    "render_welcome",
]
