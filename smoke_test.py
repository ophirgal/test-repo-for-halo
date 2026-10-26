#!/usr/bin/env python3
"""HTTP smoke test for the Hello World page (KAN-8).

Starts ``serve.py`` on an ephemeral port and exercises the real HTTP contract:
the greeting and title on ``/``, the viewport meta tag, 404 on every other
path, and ``/`` still answering 200 afterwards.

    python3 smoke_test.py      # exits 0 on pass, 1 with a FAIL line per failure

Standard library only; no framework, no network access beyond localhost.
"""

import json
import re
import sys
import threading
import urllib.error
import urllib.request

import serve
from serve import RootOnlyHandler, SIGNINS, make_server

NON_ROOT_PATHS = [
    "/index.html",
    "/docs/index.html",
    "/hello_world.txt",
    "/README.md",
    "/foo/bar",
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

    # --- Last-login feature checks (BENCH-2) ---

    # Clean signins.json so profile checks start from a known state.
    if SIGNINS.exists():
        SIGNINS.unlink()

    # Check 1: no sign-ins → first sign-in
    status, _, body = get(base, "/profile")
    checks.check("profile no-signins status", status == 200, "200", status)
    checks.check(
        "profile no-signins shows Demo User",
        "Demo User" in body,
        "'Demo User' in body",
        body[:200],
    )
    checks.check(
        "profile no-signins shows first sign-in",
        "Last login: first sign-in" in body,
        "'Last login: first sign-in'",
        body[:200],
    )

    # Check 2: one sign-in → still first sign-in
    status, _, _ = get(base, "/")
    status, _, body = get(base, "/profile")
    checks.check(
        "profile single-signin shows first sign-in",
        "Last login: first sign-in" in body,
        "'Last login: first sign-in'",
        body[:200],
    )

    # Check 3: returning visitor (two sign-ins) → shows timestamp
    status, _, _ = get(base, "/")
    status, _, body = get(base, "/profile")
    checks.check("profile returning status", status == 200, "200", status)
    checks.check(
        "profile returning shows Demo User",
        "Demo User" in body,
        "'Demo User' in body",
        body[:200],
    )
    checks.check(
        "profile returning does NOT show first sign-in",
        "first sign-in" not in body,
        "'first sign-in' absent",
        body[:200],
    )
    checks.check(
        "profile returning shows Last login with timestamp",
        "Last login: 20" in body,
        "'Last login: 20...' (ISO 8601 timestamp)",
        body[:200],
    )

    # Check 4: sign-in recording appends to file
    data = json.loads(SIGNINS.read_text())
    checks.check(
        "signins.json is a list with 2 entries",
        isinstance(data, list) and len(data) == 2,
        "list of length 2",
        f"type={type(data).__name__}, len={len(data) if isinstance(data, list) else 'N/A'}",
    )

    # Check 5: persistence — data survives handler re-reads
    status, _, body = get(base, "/profile")
    checks.check(
        "profile still shows timestamp after re-read",
        "Last login: 20" in body,
        "'Last login: 20...'",
        body[:200],
    )

    # Check 6: HEAD /profile returns 200
    checks.check("HEAD /profile status", head(base, "/profile") == 200, "200", head(base, "/profile"))

    # Check 7: backward compat — GET / still returns Hello World after profile checks
    status, _, body = get(base, "/")
    checks.check(
        "GET / greeting after profile checks",
        "Hello World" in body,
        "'Hello World' in the body",
        body[:120],
    )

    # Cleanup signins.json
    if SIGNINS.exists():
        SIGNINS.unlink()

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
