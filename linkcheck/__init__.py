"""Offline link checker for static HTML sites (standard library only)."""

from linkcheck.check import check_site
from linkcheck.extract import Link, PageDecodeError, extract_links

__all__ = ["Link", "PageDecodeError", "check_site", "extract_links"]
