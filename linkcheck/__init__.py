"""Offline link checker for static HTML sites (standard library only)."""

from linkcheck.extract import Link, PageDecodeError, extract_links

__all__ = ["Link", "PageDecodeError", "extract_links"]
