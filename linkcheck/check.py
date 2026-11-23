"""Check every HTML page under a root directory.

Each link is classified in this order: ignored (fnmatch on the target as
written), external (any scheme other than none or ``file``, or a
scheme-relative ``//host/x``), internal. Internal links are resolved to a
filesystem path and must stay inside the root: containment is decided on the
symlink-resolved path before the target is probed or read, so a link that
escapes the root is reported as ``outside-root`` and never opened.
"""

import fnmatch
import os
from typing import Dict, Iterable, List, NamedTuple, Tuple, Union
from urllib.parse import unquote, urlsplit

from linkcheck.extract import Page, PageDecodeError, parse_page

LOCAL_FILE_HOSTS = ("", "localhost")


class Finding(NamedTuple):
    path: str
    line: int
    kind: str
    target: str


class External(NamedTuple):
    path: str
    line: int
    target: str


class SiteResult(NamedTuple):
    pages: int
    links: int
    ignored: int
    external: Tuple[External, ...]
    findings: Tuple[Finding, ...]


class LinkcheckIOError(Exception):
    """A page under the root could not be read."""

    def __init__(self, path, reason):
        self.path = str(path)
        self.reason = reason
        super().__init__(f"{self.path}: cannot read: {reason}")


def _inside(path: str, root: str) -> bool:
    return os.path.commonpath([root, path]) == root


class _Checker:
    def __init__(self, root: str, ignore: Iterable[str]):
        self.root = os.path.realpath(root)
        self.ignore = tuple(ignore)
        self.cache: Dict[str, Union[Page, PageDecodeError]] = {}
        self.links = 0
        self.ignored = 0
        self.external: List[External] = []
        self.findings: List[Finding] = []

    def rel(self, path: str) -> str:
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def page(self, real: str) -> Union[Page, PageDecodeError]:
        """Parse a page at most once (keyed by its real path)."""
        if real not in self.cache:
            try:
                self.cache[real] = parse_page(real)
            except PageDecodeError as exc:
                self.cache[real] = exc
            except OSError as exc:
                raise LinkcheckIOError(self.rel(real), exc.strerror or exc) from exc
        return self.cache[real]

    def crawl(self) -> List[str]:
        def fail(exc):
            raise LinkcheckIOError(self.rel(exc.filename or self.root), exc.strerror or exc)

        pages = []
        for dirpath, dirnames, filenames in os.walk(self.root, onerror=fail):
            dirnames.sort()
            for name in sorted(filenames):
                if not name.lower().endswith(".html"):
                    continue
                path = os.path.join(dirpath, name)
                if _inside(os.path.realpath(path), self.root):
                    pages.append(path)
        return pages

    def run(self) -> SiteResult:
        pages = self.crawl()
        for path in pages:
            self.check_page(path)
        return SiteResult(
            pages=len(pages),
            links=self.links,
            ignored=self.ignored,
            external=tuple(sorted(self.external)),
            findings=tuple(sorted(self.findings)),
        )

    def check_page(self, path: str) -> None:
        rel = self.rel(path)
        page = self.page(os.path.realpath(path))
        if isinstance(page, PageDecodeError):
            self.findings.append(
                Finding(rel, page.line, "decode-error", f"byte {page.offset}")
            )
            return
        for line in page.empty_lines:
            self.findings.append(Finding(rel, line, "empty-link", ""))
        for link in page.links:
            if any(fnmatch.fnmatchcase(link.target, pat) for pat in self.ignore):
                self.ignored += 1
                continue
            self.links += 1
            self.check_link(path, rel, link.target, link.line)

    def check_link(self, page_path: str, page_rel: str, target: str, line: int) -> None:
        parts = urlsplit(target)
        scheme = parts.scheme.lower()
        if scheme not in ("", "file") or (scheme == "" and parts.netloc):
            self.external.append(External(page_rel, line, target))
            return

        def finding(kind: str, shown: str) -> None:
            self.findings.append(Finding(page_rel, line, kind, shown))

        if scheme == "file" and parts.netloc.lower() not in LOCAL_FILE_HOSTS:
            finding("outside-root", target)
            return

        path = unquote(parts.path)
        page_dir = os.path.dirname(page_path)
        if not path:
            candidate = page_path
        elif path.startswith("/"):
            # file:///abs is a filesystem path; /x is relative to the root.
            candidate = path if scheme == "file" else os.path.join(self.root, path.lstrip("/"))
        else:
            candidate = os.path.join(page_dir, path)
        lexical = os.path.normpath(candidate)

        try:
            real = os.path.realpath(lexical)
            if not _inside(real, self.root):
                finding("outside-root", target)
                return
            if path.endswith("/") or os.path.isdir(real):
                lexical = os.path.join(lexical, "index.html")
                real = os.path.realpath(os.path.join(real, "index.html"))
                if not _inside(real, self.root):
                    finding("outside-root", target)
                    return
            exists = os.path.exists(real)
        except ValueError:  # e.g. an embedded NUL byte
            finding("missing-target", target)
            return

        shown = self.rel(lexical) if _inside(lexical, self.root) else self.rel(real)
        if not exists:
            finding("missing-target", shown)
            return
        if not parts.fragment or not real.lower().endswith(".html") or not os.path.isfile(real):
            return
        page = self.page(real)
        if isinstance(page, PageDecodeError):
            return  # that page already reports its own decode-error
        if unquote(parts.fragment) not in page.anchors:
            finding("missing-anchor", f"{shown}#{parts.fragment}")


def check_site(root, ignore: Iterable[str] = ()) -> SiteResult:
    """Check every ``.html`` page under ``root``.

    ``ignore`` holds fnmatch patterns (case-sensitive) matched against each
    link's target as written; a matching link is dropped before it is
    classified and counted only in ``ignored``.

    Raises ``NotADirectoryError`` if ``root`` is not a directory and
    ``LinkcheckIOError`` if a page cannot be read.
    """
    root = os.fspath(root)
    if not os.path.isdir(root):
        raise NotADirectoryError(f"{root}: not a directory")
    return _Checker(root, ignore).run()
