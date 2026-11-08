#!/usr/bin/env python3
"""HTTP smoke test for the Hello World page (KAN-8).

Starts ``serve.py`` on an ephemeral port and exercises the real HTTP contract:
the greeting and title on ``/``, the viewport meta tag, 404 on every other
path, and ``/`` still answering 200 afterwards.

    python3 smoke_test.py      # exits 0 on pass, 1 with a FAIL line per failure

Standard library only; no framework, no network access beyond localhost.
"""

import re
import sys
import threading
import urllib.error
import urllib.request

import serve
from serve import RootOnlyHandler, make_server

NON_ROOT_PATHS = [
    "/index.html",
    "/docs/index.html",
    "/hello_world.txt",
    "/README.md",
    "/foo/bar",
]


# HALO-93 — paths that look like /jungle but must stay 404.
JUNGLE_LOOKALIKE_PATHS = [
    "/jungle/",
    "/jungle2",
    "/jungles",
    "/other",
    "/jungle.html",
    "/docs/jungle.html",
]

# HALO-93 — the only colours the jungle page may use (spec FR6).
JUNGLE_PALETTE = {
    "#0F3D2E", "#155239", "#1B5E3A", "#3E8E41", "#6DBE45",
    "#6B4423", "#4A2F1A", "#F2C230", "#E8772E",
}

# HALO-93 — tokens the static, self-contained jungle page must never contain.
JUNGLE_FORBIDDEN = [
    r"<a[\s>]", r"<button\b", r"<form\b", r"<input\b", r"<script\b",
    r"<link\b", r"<img\b", r"<iframe\b", r"<audio\b", r"<video\b",
    r"@import", r"url\(", r"@keyframes", r"animation", r"transition",
    r":hover", r"http://", r"https://", r"xmlns",
]


class QuietHandler(RootOnlyHandler):
    """Same routing, without per-request noise on stderr."""

    def log_message(self, fmt, *args):
        pass


class Checks:
    """Collect every failure so one run reports them all."""

    def __init__(self):
        self.passed = 0
        self.failures = []

    def check(self, name, condition, expected, actual):
        if condition:
            self.passed += 1
        else:
            self.failures.append(f"FAIL: {name} — expected {expected}, got {actual!r}")


def head(base, path):
    """Like get(), but issues HEAD so routing can be compared with GET."""
    request = urllib.request.Request(base + path, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as err:
        return err.code


def get(base, path):
    """Return (status, headers, body_text); a 404 is a result, not an error."""
    try:
        with urllib.request.urlopen(base + path, timeout=10) as response:
            return response.status, response.headers, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, err.headers, err.read().decode("utf-8", "replace")


def get_bytes(base, path):
    """Like get(), but returns the raw body bytes for byte-equality checks."""
    try:
        with urllib.request.urlopen(base + path, timeout=10) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as err:
        return err.code, err.headers, err.read()


def run_jungle_checks(base, checks):
    """HALO-93 — the /jungle page, its route, and the unchanged boundaries."""
    # Routes: GET, GET with a query string, and HEAD all serve the page.
    status, headers, raw = get_bytes(base, "/jungle")
    checks.check("GET /jungle status", status == 200, "200", status)
    content_type = headers.get("Content-Type", "")
    checks.check(
        "GET /jungle Content-Type",
        content_type == "text/html; charset=utf-8",
        "text/html; charset=utf-8",
        content_type,
    )
    checks.check(
        "GET /jungle body is docs/jungle.html",
        raw == serve.JUNGLE.read_bytes(),
        "the bytes of docs/jungle.html",
        raw[:120],
    )
    status, _, _ = get(base, "/jungle?x=1")
    checks.check("GET /jungle?x=1 status", status == 200, "200", status)
    checks.check("HEAD /jungle status", head(base, "/jungle") == 200, "200", head(base, "/jungle"))

    # The route table holds exactly the two fixed files.
    checks.check(
        "only two fixed routes",
        serve.ROUTES == {"/": serve.INDEX, "/jungle": serve.JUNGLE},
        "{'/': INDEX, '/jungle': JUNGLE}",
        serve.ROUTES,
    )

    # The root is byte-for-byte the file on disk: no "!" and no link to /jungle.
    status, _, root_raw = get_bytes(base, "/")
    checks.check("GET / status (HALO-93)", status == 200, "200", status)
    checks.check(
        "GET / is byte-identical to docs/index.html",
        root_raw == serve.INDEX.read_bytes(),
        "the bytes of docs/index.html",
        root_raw[:120],
    )
    root_text = root_raw.decode("utf-8", "replace")
    checks.check(
        "GET / greeting has no exclamation mark",
        "Hello World" in root_text and "Hello World!" not in root_text,
        "'Hello World' without '!'",
        root_text[:200],
    )
    checks.check(
        "GET / does not link to /jungle",
        "/jungle" not in root_text,
        "no '/jungle' in the root page",
        root_text[:200],
    )

    # Look-alikes and every existing non-root path stay 404, GET and HEAD.
    for path in JUNGLE_LOOKALIKE_PATHS + NON_ROOT_PATHS:
        status, _, body_404 = get(base, path)
        checks.check(f"GET {path} status (HALO-93)", status == 404, "404", status)
        checks.check(
            f"GET {path} is not a listing (HALO-93)",
            "Directory listing" not in body_404,
            "no directory listing",
            body_404[:120],
        )
        checks.check(f"HEAD {path} status", head(base, path) == 404, "404", head(base, path))

    # Page content.
    body = raw.decode("utf-8", "replace")
    checks.check(
        "jungle page declares English",
        re.search(r"<html\b[^>]*\blang=\"en\"", body, re.I) is not None,
        '<html lang="en">',
        body[:120],
    )
    checks.check(
        "jungle viewport meta tag",
        'name="viewport"' in body and "width=device-width" in body,
        'name="viewport" with width=device-width',
        "missing",
    )
    title = re.search(r"<title[^>]*>([^<]*)</title>", body, re.I)
    title_text = title.group(1).strip() if title else None
    checks.check(
        "jungle title",
        title_text == "Hello World! · Jungle",
        "Hello World! · Jungle",
        title_text,
    )
    headings = re.findall(r"<(h[1-6])\b", body, re.I)
    checks.check("jungle page has exactly one heading, an <h1>", headings == ["h1"], ["h1"], headings)
    h1 = re.search(r"<h1\b[^>]*>(.*?)</h1>", body, re.S | re.I)
    h1_text = " ".join(re.sub(r"<[^>]*>", " ", h1.group(1)).split()) if h1 else None
    checks.check("jungle heading text", h1_text == "Hello World!", "Hello World!", h1_text)

    found = [token for token in JUNGLE_FORBIDDEN if re.search(token, body, re.I)]
    checks.check("jungle page has no forbidden tokens", not found, "none of " + ", ".join(JUNGLE_FORBIDDEN), found)

    svgs = re.findall(r"<svg\b[^>]*>", body, re.I)
    checks.check("jungle page has decorations", len(svgs) > 0, "inline <svg> decorations", len(svgs))
    unhidden = [tag for tag in svgs if 'aria-hidden="true"' not in tag]
    checks.check("every decoration is aria-hidden", not unhidden, 'aria-hidden="true" on every <svg>', unhidden)
    checks.check("decorations contain no text", "<text" not in body.lower(), "no <text>", "found <text")

    visible = re.sub(r"<(style|svg|title)\b.*?</\1>", " ", body, flags=re.S | re.I)
    visible = re.sub(r"<!--.*?-->", " ", visible, flags=re.S)
    visible = " ".join(re.sub(r"<[^>]*>", " ", visible).split())
    checks.check("jungle visible text is only the heading", visible == "Hello World!", "Hello World!", visible)

    colours = {c.upper() for c in re.findall(r"#[0-9A-Fa-f]{3,8}\b", body)}
    checks.check(
        "jungle colours are all from the palette",
        colours <= JUNGLE_PALETTE,
        sorted(JUNGLE_PALETTE),
        sorted(colours - JUNGLE_PALETTE),
    )
    checks.check(
        "jungle page uses no rgb/hsl colours",
        re.search(r"\b(?:rgba?|hsla?)\(", body, re.I) is None,
        "hex palette colours only",
        "rgb()/hsl() found",
    )
    checks.check(
        "jungle heading, background and glow colours present",
        {"#F2C230", "#0F3D2E", "#155239"} <= colours,
        "#F2C230, #0F3D2E and #155239",
        sorted(colours),
    )

    # Same width rule as the root page (pattern copied, not shared).
    wide = [
        f"{value}{unit}"
        for value, unit in re.findall(
            r"(?:\bmin-)?width\s*[:=]\s*\"?(\d+(?:\.\d+)?)\s*(px|pt)", body, re.I
        )
        if float(value) > 375
    ]
    checks.check("jungle: no declared width wider than 375px", not wide, "no width over 375px", wide)

    secrets = re.findall(r"password|api_?key|secret|token=", body, re.I)
    checks.check("jungle page holds no secrets", not secrets, "no keys or passwords", secrets)

    # The server docstrings describe two fixed pages, not a root-only server.
    doc = serve.__doc__ or ""
    stale = [w for w in ("root-only", "exactly one document") if w in doc.lower()]
    checks.check("serve.py docstring updated", not stale, "no 'Root-only'/'exactly one document'", stale)


def run_checks(base):
    checks = Checks()

    # AC1 — localhost by default, port chosen by argument or PORT (argument
    # wins), and the usage documented in this module's header rather than in
    # README.md.
    checks.check(
        "default host is localhost",
        serve.DEFAULT_HOST == "127.0.0.1",
        "127.0.0.1",
        serve.DEFAULT_HOST,
    )
    checks.check(
        "default port",
        serve._resolve_port(["serve.py"]) == serve.DEFAULT_PORT,
        serve.DEFAULT_PORT,
        serve._resolve_port(["serve.py"]),
    )
    checks.check(
        "positional argument wins over PORT",
        serve._resolve_port(["serve.py", "8099"]) == 8099,
        8099,
        serve._resolve_port(["serve.py", "8099"]),
    )
    usage = serve.__doc__ or ""
    checks.check(
        "usage documented in the serve.py header",
        "python3 serve.py" in usage and "PORT=" in usage and "HOST=" in usage,
        "serve.py's docstring to document the command, PORT and HOST",
        usage[:120],
    )

    # AC2 — root returns 200 HTML whose main content area shows the greeting.
    status, headers, body = get(base, "/")
    checks.check("GET / status", status == 200, "200", status)
    content_type = headers.get("Content-Type", "")
    checks.check(
        "GET / Content-Type",
        content_type.startswith("text/html"),
        "a Content-Type starting with text/html",
        content_type,
    )
    main_block = re.search(r"<main\b[^>]*>(.*?)</main>", body, re.S | re.I)
    checks.check("GET / has a <main> element", main_block is not None, "<main>…</main>", body)
    if main_block:
        main_text = re.sub(r"<[^>]*>", " ", main_block.group(1))
        checks.check(
            "main content contains the greeting",
            "Hello World" in main_text,
            "'Hello World' inside <main>",
            " ".join(main_text.split()),
        )

    # AC3 — the document title contains the greeting.
    title = re.search(r"<title[^>]*>([^<]*)</title>", body, re.I)
    checks.check("document has a <title>", title is not None, "<title>…</title>", body)
    if title:
        checks.check(
            "title contains the greeting",
            "Hello World" in title.group(1),
            "'Hello World' inside <title>",
            title.group(1),
        )

    # AC4 (automated portion) — the viewport meta tag is present and set to
    # device width. The 375px render itself is a manual browser check.
    checks.check(
        "viewport meta tag present",
        'name="viewport"' in body,
        'name="viewport"',
        "no viewport meta tag",
    )
    checks.check(
        "viewport set to device width",
        "width=device-width" in body,
        "width=device-width",
        "no width=device-width",
    )

    # AC4 (static portion) — nothing declares a width wider than the 375px
    # reference viewport, so the greeting cannot be pushed off-screen.
    wide = [
        f"{value}{unit}"
        for value, unit in re.findall(
            r"(?:\bmin-)?width\s*[:=]\s*\"?(\d+(?:\.\d+)?)\s*(px|pt)", body, re.I
        )
        if float(value) > 375
    ]
    checks.check(
        "no declared width wider than 375px",
        not wide,
        "no width or min-width over 375px",
        wide,
    )

    # HEAD routes exactly like GET, so probes and browsers agree.
    checks.check("HEAD / status", head(base, "/") == 200, "200", head(base, "/"))
    checks.check(
        "HEAD /foo/bar status", head(base, "/foo/bar") == 404, "404", head(base, "/foo/bar")
    )

    # A query string on the root is still the root.
    status, _, _ = get(base, "/?x=1")
    checks.check("GET /?x=1 status", status == 200, "200", status)

    # AC5 — every other path is 404, and no directory listing is ever returned.
    for path in NON_ROOT_PATHS:
        status, _, body_404 = get(base, path)
        checks.check(f"GET {path} status", status == 404, "404", status)
        checks.check(
            f"GET {path} is not a listing",
            "Directory listing" not in body_404,
            "no directory listing",
            body_404[:120],
        )

    # AC6 — the root still works after the 404 round.
    status, _, body = get(base, "/")
    checks.check("GET / status after 404s", status == 200, "200", status)
    checks.check(
        "GET / greeting after 404s",
        "Hello World" in body,
        "'Hello World' in the body",
        body[:120],
    )

    run_jungle_checks(base, checks)

    return checks


def main():
    server = make_server("127.0.0.1", 0, QuietHandler)
    base = "http://127.0.0.1:%d" % server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        checks = run_checks(base)
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()

    if checks.failures:
        for failure in checks.failures:
            print(failure)
        print(f"{len(checks.failures)} check(s) failed, {checks.passed} passed")
        return 1
    print(f"OK: {checks.passed} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
