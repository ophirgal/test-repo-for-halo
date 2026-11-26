#!/usr/bin/env python3
"""Fixed-route HTTP server for the Hello World pages (KAN-8, HALO-93, SCRUM-119, SCRUM-126).

Serves two fixed pages: ``docs/index.html`` at ``/`` and
``docs/jungle.html`` at ``/jungle``, matched exactly (a query string is
ignored). Three more routes answer: the health check ``/healthz`` (SCRUM-122),
the guestbook page ``/guestbook`` (SCRUM-126) and the key-value store under
``/kv/`` (SCRUM-119), all described below.
Every other path returns 404 — including ``/kv`` without the
slash, ``/jungle/``, ``/jungle.html``, ``/index.html``, ``/docs/index.html``
and the repository's own files — so there is no directory listing and no file
is ever chosen from request input.

Health check (SCRUM-122): ``GET /healthz`` answers 200,
``Content-Type: application/json``, body ``{"status": "ok"}``; ``HEAD /healthz``
sends the same headers with no body. The path is matched exactly (a query
string is ignored; ``/healthz/`` is a 404). The answer never touches the store,
so it is 200 whatever the store's state, and it has no authentication.

Guestbook (SCRUM-126, package ``guestbook``), backed by the JSON Lines file
``GUESTBOOK_PATH`` (default ``./guestbook.jsonl``):

    GET|HEAD /guestbook   200, the page: a one-line form and the latest 20
                          messages, newest first, each with its send time
    POST     /guestbook   form field ``message`` (urlencoded); 303 to
                          /guestbook when saved, 400 with the page in an error
                          state when empty or over 200 characters (never cut)

The path is matched exactly (a query string is ignored). A POST also answers
400 (bad Content-Length or UTF-8), 413 (over 64 KiB, unread), 415 (not a
form) and 500 (file unwritable; its directory is never created). ``POST`` to
any other path, and ``PUT``/``DELETE /guestbook``, answer the standard 501.

Newsletter signup (SCRUM-103, package ``newsletter``), backed by the JSON
Lines file ``NEWSLETTER_PATH`` (default ``./newsletter.jsonl``):

    GET|HEAD /newsletter          200, Welcome
    GET|HEAD /newsletter/signup   200, the signup form (name and email)
    POST     /newsletter/signup   fields ``name`` and ``email`` (urlencoded);
                                  303 to /newsletter/thanks when valid, for a
                                  new and an already-subscribed address alike;
                                  400 with the form and inline errors when a
                                  field is empty or malformed; 500 with the
                                  form in its "submission failed" state when
                                  the file cannot be written
    GET|HEAD /newsletter/thanks   200, Confirmation (the same for everyone)
    GET|HEAD /newsletter/form.js  200, the form's fixed script

Paths match exactly (a query string is ignored); ``/newsletter/`` and every
other look-alike is a 404. A POST also answers 400 (bad Content-Length or
UTF-8), 413 (over 64 KiB, unread) and 415 (not a form). No route returns the
signups: they are exported only by ``python3 -m newsletter export`` on the
host. With ``HOST=0.0.0.0`` anyone on the network can submit signups, but no
route can read them.

Key-value store (``kvstore``), backed by the log file ``KV_PATH`` (default
``./kv.log``); keys never touch the filesystem:

    GET    /kv/                 200, JSON array of live keys (sorted)
    GET    /kv/<key>            200 with the JSON value, or 404
    PUT    /kv/<key>[?ttl=<s>]  JSON body; 204 (400 bad input, 413 over 64 KiB)
    DELETE /kv/<key>            204, or 404

``<key>`` is the percent-decoded path after ``/kv/`` and may contain ``/``.
Errors answer ``{"error": "..."}``; a log corrupt in the middle makes every
``/kv/`` request answer 503 while the pages keep working.

Usage
-----
    python3 serve.py                 # http://127.0.0.1:8000/
    python3 serve.py 9000            # port from the positional argument
    PORT=9000 python3 serve.py       # port from the environment
    HOST=0.0.0.0 python3 serve.py    # bind all interfaces (opt-in; /kv/ and /guestbook have no auth)
    KV_PATH=/tmp/kv.log python3 serve.py  # store file (default ./kv.log)
    GUESTBOOK_PATH=/tmp/gb.jsonl python3 serve.py  # guestbook file (default ./guestbook.jsonl)
    NEWSLETTER_PATH=/tmp/nl.jsonl python3 serve.py # signup file (default ./newsletter.jsonl)
    python3 smoke_test.py            # run the HTTP checks

The positional argument wins over ``PORT``; ``PORT`` wins over the default
8000. The default host is ``127.0.0.1``; binding beyond localhost is explicit.
Stop the server with Ctrl-C. This is a local proof-of-life server, not a
production host.
"""

import http.server
import json
import math
import os
import re
import sys
import threading
import urllib.parse
from pathlib import Path

import guestbook
import newsletter
from kvstore import CorruptLogError, KVStore, check_key

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_KV_PATH = "./kv.log"
KV_PREFIX = "/kv/"
KV_MAX_BODY = 65536
# Marks a /kv/ answer with no body (204). A stored JSON null is a real value.
NO_BODY = object()

INDEX = Path(__file__).resolve().parent / "docs" / "index.html"
JUNGLE = Path(__file__).resolve().parent / "docs" / "jungle.html"

# Exact request path -> fixed file. The only files the server can ever send.
ROUTES = {"/": INDEX, "/jungle": JUNGLE}

# Health check (SCRUM-122): exact path and its fixed, store-independent answer.
HEALTH_PATH = "/healthz"
HEALTH_BODY = b'{"status": "ok"}'

# Guestbook (SCRUM-126): exact path, its message file and its page headers.
GUESTBOOK_ROUTE = "/guestbook"
DEFAULT_GUESTBOOK_PATH = "./guestbook.jsonl"
FORM_TYPE = "application/x-www-form-urlencoded"
GUESTBOOK_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
    "base-uri 'none'; frame-ancestors 'none'"
)

# Newsletter signup (SCRUM-103): exact paths, the signup file and page headers.
NEWSLETTER_ROUTE = newsletter.pages.WELCOME_PATH
NEWSLETTER_SIGNUP = newsletter.pages.SIGNUP_PATH
NEWSLETTER_THANKS = newsletter.pages.THANKS_PATH
NEWSLETTER_JS = newsletter.pages.SCRIPT_PATH
DEFAULT_NEWSLETTER_PATH = "./newsletter.jsonl"
NEWSLETTER_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; form-action 'self'; "
    "base-uri 'none'; frame-ancestors 'none'"
)


class KVRequestError(Exception):
    """An HTTP error answer for a ``/kv/`` request."""

    def __init__(self, status, message, close=False):
        super().__init__(message)
        self.status = status
        self.close = close


def _reject_constant(name):
    raise ValueError(f"value JSON: {name} is not allowed")


def _parse_ttl(query):
    values = urllib.parse.parse_qs(query, keep_blank_values=True).get("ttl")
    if values is None:
        return None
    if len(values) != 1:
        raise KVRequestError(400, "ttl: give ttl at most once")
    try:
        ttl = float(values[0])
    except ValueError:
        raise KVRequestError(400, f"ttl: {values[0]!r} is not a number of seconds") from None
    if not math.isfinite(ttl) or ttl <= 0:
        raise KVRequestError(400, f"ttl: must be finite and greater than 0, got {values[0]!r}")
    return ttl


class RootOnlyHandler(http.server.BaseHTTPRequestHandler):
    """Answer ``/`` and ``/jungle`` with their fixed pages, ``/healthz`` with
    a fixed JSON answer and ``/kv/`` from the store; everything else 404.

    Deliberately not ``SimpleHTTPRequestHandler``: there are no directory
    semantics, no listings, and no path built from the request, so path
    traversal has no surface here.
    """

    server_version = "HelloWorld/1.0"

    def _route(self):
        """Return the fixed file for an exact path match, or None."""
        return ROUTES.get(urllib.parse.urlsplit(self.path).path)

    def _send_index_headers(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

    def _health(self):
        """Answer GET/HEAD ``/healthz`` and return True; otherwise False.

        Never touches the store, so the answer is the same whatever its state.
        """
        if urllib.parse.urlsplit(self.path).path != HEALTH_PATH:
            return False
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(HEALTH_BODY)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(HEALTH_BODY)
        return True

    # -- /guestbook (SCRUM-126) -------------------------------------------

    def _guestbook(self):
        """Answer GET/HEAD/POST ``/guestbook`` and return True; otherwise False."""
        if urllib.parse.urlsplit(self.path).path != GUESTBOOK_ROUTE:
            return False
        if self.command == "POST":
            self._guestbook_post()
            return True
        try:
            records = self.server.guestbook_store().latest()
        except OSError:
            self.send_error(500, "guestbook file cannot be read")
            return True
        self._guestbook_page(200, guestbook.render(records))
        return True

    def _guestbook_page(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", GUESTBOOK_CSP)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _guestbook_post(self):
        try:
            body = self._kv_body()  # the same Content-Length rules as /kv/
        except KVRequestError as err:
            self.send_error(err.status, str(err))  # send_error closes the connection
            return
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type != FORM_TYPE:
            self.send_error(415, f"expected {FORM_TYPE}")
            return
        try:
            fields = urllib.parse.parse_qs(
                body.decode("utf-8"), keep_blank_values=True, encoding="utf-8", errors="strict"
            )
        except (UnicodeDecodeError, ValueError):
            self.send_error(400, "form body is not valid UTF-8")
            return
        raw = (fields.get("message") or [""])[0]
        text, error, length = guestbook.check(raw)
        store = self.server.guestbook_store()
        try:
            if error is not None:
                page = guestbook.render(store.latest(), error=error, value=raw, length=length)
                self._guestbook_page(400, page)
                return
            store.append(text)
        except OSError:
            self.send_error(500, "guestbook file cannot be read or written")
            return
        self.send_response(303)
        self.send_header("Location", GUESTBOOK_ROUTE)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # -- /newsletter (SCRUM-103) -------------------------------------------

    def _newsletter(self):
        """Answer the exact newsletter paths and return True; otherwise False.

        POST is answered at ``/newsletter/signup`` only, so a POST anywhere
        else keeps the standard 501.
        """
        path = urllib.parse.urlsplit(self.path).path
        if self.command == "POST":
            if path != NEWSLETTER_SIGNUP:
                return False
            self._newsletter_post()
            return True
        if path == NEWSLETTER_ROUTE:
            self._newsletter_send(200, newsletter.render_welcome())
        elif path == NEWSLETTER_SIGNUP:
            self._newsletter_send(200, newsletter.render_form())
        elif path == NEWSLETTER_THANKS:
            self._newsletter_send(200, newsletter.render_thanks())
        elif path == NEWSLETTER_JS:
            self._newsletter_send(200, newsletter.FORM_JS, "text/javascript; charset=utf-8")
        else:
            return False
        return True

    def _newsletter_send(self, status, body, content_type="text/html; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", NEWSLETTER_CSP)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _newsletter_post(self):
        try:
            body = self._kv_body()  # the same Content-Length rules as /kv/
        except KVRequestError as err:
            self.send_error(err.status, str(err))  # send_error closes the connection
            return
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type != FORM_TYPE:
            self.send_error(415, f"expected {FORM_TYPE}")
            return
        try:
            fields = urllib.parse.parse_qs(
                body.decode("utf-8"), keep_blank_values=True, encoding="utf-8", errors="strict"
            )
        except (UnicodeDecodeError, ValueError):
            self.send_error(400, "form body is not valid UTF-8")
            return
        values = {f: (fields.get(f) or [""])[0] for f in ("name", "email")}
        name, email, errors = newsletter.check(values["name"], values["email"])
        if errors:
            self._newsletter_send(400, newsletter.render_form(values, errors))
            return
        try:
            self.server.newsletter_store().add(name, email)
        except OSError as err:
            self.log_error("newsletter store unavailable: %s", err)  # errno and path, never the signup
            self._newsletter_send(500, newsletter.render_form(values, failed=True))
            return
        # The same answer whether the address was new or already subscribed.
        self.send_response(303)
        self.send_header("Location", NEWSLETTER_THANKS)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # -- /kv/ store routes (SCRUM-119) -----------------------------------

    def _kv_key(self):
        """The key under /kv/, or None when the path is not a store route."""
        path = urllib.parse.urlsplit(self.path).path
        if not path.startswith(KV_PREFIX):
            return None
        return path[len(KV_PREFIX):]

    def _kv_send(self, status, payload=NO_BODY, close=False):
        body = b""
        self.send_response(status)
        if payload is not NO_BODY:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
        if close:
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def _kv_body(self):
        """Read the PUT body, judged by Content-Length before reading it."""
        lengths = self.headers.get_all("Content-Length") or []
        if len(set(lengths)) != 1 or not re.fullmatch(r"[0-9]+", lengths[0].strip()):
            raise KVRequestError(400, "a valid Content-Length header is required", close=True)
        length = int(lengths[0])
        if length > KV_MAX_BODY:
            raise KVRequestError(
                413, f"request body is {length} bytes, at most {KV_MAX_BODY} allowed", close=True
            )
        return self.rfile.read(length)

    def _kv_handle(self, raw_key):
        method = self.command
        body = self._kv_body() if method == "PUT" else None
        store = self.server.kv_open()
        try:
            key = urllib.parse.unquote(raw_key, encoding="utf-8", errors="strict")
        except UnicodeDecodeError:
            raise KVRequestError(400, "key printable: key is not valid percent-encoded UTF-8") from None
        if method in ("GET", "HEAD") and key == "":
            return 200, store.keys()
        check_key(key)
        if method in ("GET", "HEAD"):
            return 200, store.get(key)
        if method == "DELETE":
            store.delete(key)
            return 204, NO_BODY
        ttl = _parse_ttl(urllib.parse.urlsplit(self.path).query)
        try:
            value = json.loads(body.decode("utf-8"), parse_constant=_reject_constant)
        except ValueError as err:  # invalid UTF-8, BOM, bad JSON, NaN, huge ints
            raise KVRequestError(400, f"value JSON: request body is not valid JSON ({err})") from None
        store.set(key, value, ttl=ttl)
        return 204, NO_BODY

    def _kv_dispatch(self, raw_key):
        """Answer a /kv/ request, mapping store errors to HTTP statuses."""
        try:
            status, payload = self._kv_handle(raw_key)
        except KVRequestError as err:
            self._kv_send(err.status, {"error": str(err)}, close=err.close)
        except CorruptLogError as err:
            self._kv_send(503, {"error": str(err)})
        except KeyError as err:
            self._kv_send(404, {"error": f"key not found: {err.args[0]}"})
        except ValueError as err:
            self._kv_send(400, {"error": str(err)})
        except OSError as err:
            self._kv_send(500, {"error": f"store I/O error: {err}"})
        else:
            self._kv_send(status, payload)

    # -- methods -----------------------------------------------------------

    def do_GET(self):
        raw_key = self._kv_key()
        if raw_key is not None:
            self._kv_dispatch(raw_key)
            return
        if self._health() or self._guestbook() or self._newsletter():
            return
        target = self._route()
        if target is None:
            self.send_error(404)
            return
        body = target.read_bytes()
        self._send_index_headers(body)
        self.wfile.write(body)

    def do_HEAD(self):
        raw_key = self._kv_key()
        if raw_key is not None:
            self._kv_dispatch(raw_key)
            return
        if self._health() or self._guestbook() or self._newsletter():
            return
        target = self._route()
        if target is None:
            self.send_error(404)
            return
        self._send_index_headers(target.read_bytes())

    def _kv_only(self):
        """PUT/DELETE: served under /kv/ only; elsewhere the standard 501."""
        raw_key = self._kv_key()
        if raw_key is None:
            self.send_error(501, "Unsupported method (%r)" % self.command)
            return
        self._kv_dispatch(raw_key)

    do_PUT = _kv_only
    do_DELETE = _kv_only

    def do_POST(self):
        """POST: served at /guestbook and /newsletter/signup only; elsewhere the standard 501."""
        if not (self._guestbook() or self._newsletter()):
            self.send_error(501, "Unsupported method (%r)" % self.command)


class KVHTTPServer(http.server.ThreadingHTTPServer):
    """The threading server, holding the one store shared by every request."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kv_store = None
        self.kv_error = None
        self._kv_lock = threading.Lock()
        self._guestbook = None
        self._guestbook_lock = threading.Lock()
        self._newsletter = None
        self._newsletter_lock = threading.Lock()

    def kv_open(self):
        """Return the shared store, opening ``KV_PATH`` on first use.

        A log corrupt in the middle is remembered: this raises its
        ``CorruptLogError`` every time, so ``/kv/`` answers 503.
        """
        with self._kv_lock:
            if self.kv_store is None and self.kv_error is None:
                path = os.environ.get("KV_PATH") or DEFAULT_KV_PATH
                try:
                    self.kv_store = KVStore(path)
                except CorruptLogError as err:
                    self.kv_error = err
            if self.kv_error is not None:
                raise CorruptLogError(self.kv_error.path, self.kv_error.lineno)
            return self.kv_store

    def guestbook_store(self):
        """Return the shared guestbook store for ``GUESTBOOK_PATH``.

        Built on first use; it reads its file lazily and never creates it.
        """
        with self._guestbook_lock:
            if self._guestbook is None:
                path = os.environ.get("GUESTBOOK_PATH") or DEFAULT_GUESTBOOK_PATH
                self._guestbook = guestbook.GuestbookStore(path)
            return self._guestbook

    def newsletter_store(self):
        """Return the shared signup store for ``NEWSLETTER_PATH``.

        Built on first use; it reads its file lazily and never creates it.
        """
        with self._newsletter_lock:
            if self._newsletter is None:
                path = os.environ.get("NEWSLETTER_PATH") or DEFAULT_NEWSLETTER_PATH
                self._newsletter = newsletter.SignupStore(path)
            return self._newsletter

    def server_close(self):
        super().server_close()
        if self.kv_store is not None:
            self.kv_store.close()


def make_server(host=DEFAULT_HOST, port=DEFAULT_PORT, handler=RootOnlyHandler):
    """Build a server bound to ``host:port``. Port 0 picks an ephemeral port."""
    return KVHTTPServer((host, port), handler)


def _resolve_port(argv):
    raw = argv[1] if len(argv) > 1 else os.environ.get("PORT")
    if raw is None or raw == "":
        return DEFAULT_PORT
    try:
        port = int(raw)
    except ValueError:
        raise SystemExit(f"invalid port {raw!r}: expected an integer 0-65535")
    if not 0 <= port <= 65535:
        raise SystemExit(f"invalid port {port}: expected an integer 0-65535")
    return port


def main(argv):
    host = os.environ.get("HOST") or DEFAULT_HOST
    port = _resolve_port(argv)
    server = make_server(host, port)
    try:
        server.kv_open()  # a torn-tail warning shows on stderr now
    except CorruptLogError as err:
        print(f"kvstore unavailable, /kv/ will answer 503: {err}", file=sys.stderr, flush=True)
    except OSError as err:
        # The pages still serve; /kv/ retries the open and answers 500 meanwhile.
        print(f"kvstore unavailable, /kv/ will answer 500: {err}", file=sys.stderr, flush=True)
    bound_host, bound_port = server.server_address[:2]
    print(f"serving Hello World on http://{bound_host}:{bound_port}/ (Ctrl-C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
