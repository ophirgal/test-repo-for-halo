#!/usr/bin/env python3
"""Root-only HTTP server for the Hello World page (KAN-8).

Serves exactly one document, ``docs/index.html``, and only at the root path.
Every other path returns 404 — including ``/index.html``, ``/docs/index.html``
and the repository's own files — so there is no directory listing and no file
is ever chosen from request input.

Usage
-----
    python3 serve.py                 # http://127.0.0.1:8000/
    python3 serve.py 9000            # port from the positional argument
    PORT=9000 python3 serve.py       # port from the environment
    HOST=0.0.0.0 python3 serve.py    # bind all interfaces (opt-in)
    python3 smoke_test.py            # run the HTTP checks

The positional argument wins over ``PORT``; ``PORT`` wins over the default
8000. The default host is ``127.0.0.1``; binding beyond localhost is explicit.
Stop the server with Ctrl-C. This is a local proof-of-life server, not a
production host.
"""

import http.server
import os
import sys
import urllib.parse
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

INDEX = Path(__file__).resolve().parent / "docs" / "index.html"


class RootOnlyHandler(http.server.BaseHTTPRequestHandler):
    """Answer ``/`` with the greeting page; answer everything else with 404.

    Deliberately not ``SimpleHTTPRequestHandler``: there are no directory
    semantics, no listings, and no path built from the request, so path
    traversal has no surface here.
    """

    server_version = "HelloWorld/1.0"

    def _is_root(self):
        return urllib.parse.urlsplit(self.path).path == "/"

    def _send_index_headers(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

    def do_GET(self):
        if not self._is_root():
            self.send_error(404)
            return
        body = INDEX.read_bytes()
        self._send_index_headers(body)
        self.wfile.write(body)

    def do_HEAD(self):
        if not self._is_root():
            self.send_error(404)
            return
        self._send_index_headers(INDEX.read_bytes())


def make_server(host=DEFAULT_HOST, port=DEFAULT_PORT, handler=RootOnlyHandler):
    """Build a server bound to ``host:port``. Port 0 picks an ephemeral port."""
    return http.server.ThreadingHTTPServer((host, port), handler)


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
