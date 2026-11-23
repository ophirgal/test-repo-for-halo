"""Extract links, empty links and anchor names from one UTF-8 HTML page.

Only ``href``/``src`` on ``a``, ``link``, ``img`` and ``script`` count.
``html.parser`` lower-cases tag and attribute names, unescapes entities in
attribute values and treats ``<script>``/``<style>`` bodies as raw text, so
markup inside them and CSS ``url()`` are never seen as links.
"""

from html.parser import HTMLParser
from typing import FrozenSet, List, NamedTuple, Tuple

_BOM = b"\xef\xbb\xbf"

# tag -> (attribute, kind)
_LINK_ATTRS = {
    "a": ("href", "anchor"),
    "img": ("src", "image"),
    "link": ("href", "stylesheet"),
    "script": ("src", "script"),
}


class Link(NamedTuple):
    """One link as written in a page."""

    target: str
    line: int
    kind: str


class Page(NamedTuple):
    """Everything one parse of a page yields."""

    links: Tuple[Link, ...]
    empty_lines: Tuple[int, ...]
    anchors: FrozenSet[str]


class PageDecodeError(ValueError):
    """A page is not valid UTF-8."""

    def __init__(self, path, offset: int, line: int):
        self.path = str(path)
        self.offset = offset
        self.line = line
        super().__init__(
            f"{self.path}: not valid UTF-8 at byte {offset} (line {line})"
        )


def _decode(path, data: bytes) -> str:
    skip = len(_BOM) if data.startswith(_BOM) else 0
    try:
        return data[skip:].decode("utf-8")
    except UnicodeDecodeError as exc:
        offset = skip + exc.start
        raise PageDecodeError(path, offset, data.count(b"\n", 0, offset) + 1) from None


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: List[Link] = []
        self.empty_lines: List[int] = []
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        first = {}
        for name, value in attrs:
            first.setdefault(name, value)
        if first.get("id"):
            self.anchors.add(first["id"])
        if tag == "a" and first.get("name"):
            self.anchors.add(first["name"])
        spec = _LINK_ATTRS.get(tag)
        if spec is None:
            return
        attr, kind = spec
        if attr not in first:
            return
        target = (first[attr] or "").strip()
        if target:
            self.links.append(Link(target, line, kind))
        else:
            self.empty_lines.append(line)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def parse_page(path) -> Page:
    """Parse ``path`` once: links in document order, empty-link lines, anchors.

    Raises ``PageDecodeError`` if the file is not valid UTF-8 and ``OSError``
    if it cannot be read.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    parser = _Parser()
    parser.feed(_decode(path, data))
    parser.close()
    return Page(tuple(parser.links), tuple(parser.empty_lines), frozenset(parser.anchors))


def extract_links(path) -> List[Link]:
    """Return the page's links in document order."""
    return list(parse_page(path).links)
