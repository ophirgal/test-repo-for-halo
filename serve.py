#!/usr/bin/env python3
"""Fixed-route HTTP server for the Hello World pages (KAN-8, HALO-93, SCRUM-119).

Serves two fixed pages: ``docs/index.html`` at ``/`` and
``docs/jungle.html`` at ``/jungle``, matched exactly (a query string is
ignored). The one exception is the key-value store under ``/kv/`` (SCRUM-119,
see below). Every other path returns 404 — including ``/kv`` without the
slash, ``/jungle/``, ``/jungle.html``, ``/index.html``, ``/docs/index.html``
and the repository's own files — so there is no directory listing and no file
is ever chosen from request input.

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
    HOST=0.0.0.0 python3 serve.py    # bind all interfaces (opt-in; /kv/ has no auth)
    KV_PATH=/tmp/kv.log python3 serve.py  # store file (default ./kv.log)
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

from kvstore import CorruptLogError, KVStore, check_key

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_KV_PATH = "./kv.log"
KV_PREFIX = "/kv/"
KV_MAX_BODY = 65536

INDEX = Path(__file__).resolve().parent / "docs" / "index.html"
JUNGLE = Path(__file__).resolve().parent / "docs" / "jungle.html"

# Exact request path -> fixed file. The only files the server can ever send.
ROUTES = {"/": INDEX, "/jungle": JUNGLE}


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
    """Answer ``/`` and ``/jungle`` with their fixed pages and ``/kv/`` from
    the store; everything else 404.

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

    # -- /kv/ store routes (SCRUM-119) -----------------------------------

    def _kv_key(self):
        """The key under /kv/, or None when the path is not a store route."""
        path = urllib.parse.urlsplit(self.path).path
        if not path.startswith(KV_PREFIX):
            return None
        return path[len(KV_PREFIX):]

    def _kv_send(self, status, payload=None, close=False):
        body = b""
        self.send_response(status)
        if payload is not None:
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
            return 204, None
        ttl = _parse_ttl(urllib.parse.urlsplit(self.path).query)
        try:
            value = json.loads(body.decode("utf-8"), parse_constant=_reject_constant)
        except ValueError as err:  # invalid UTF-8, BOM, bad JSON, NaN, huge ints
            raise KVRequestError(400, f"value JSON: request body is not valid JSON ({err})") from None
        store.set(key, value, ttl=ttl)
        return 204, None

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


class KVHTTPServer(http.server.ThreadingHTTPServer):
    """The threading server, holding the one store shared by every request."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kv_store = None
        self.kv_error = None
        self._kv_lock = threading.Lock()

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
