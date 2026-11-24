"""SCRUM-122 — the /healthz route in serve.py, end to end."""

import http.client
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

import serve
from kvstore import encode_record

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOK_ALIKES = ("/healthz/", "/healthz.json", "/HEALTHZ", "/health", "/healthzx")


class QuietHandler(serve.RootOnlyHandler):
    def log_message(self, fmt, *args):
        pass


class HealthzTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.kv_path = os.path.join(self.tmp.name, "kv.log")
        self.use_kv_path(self.kv_path)

    def use_kv_path(self, path):
        patcher = mock.patch.dict(os.environ, {"KV_PATH": path})
        patcher.start()
        self.addCleanup(patcher.stop)

    def start(self):
        server = serve.make_server("127.0.0.1", 0, QuietHandler)  # free port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def stop():
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()

        self.addCleanup(stop)
        self.port = server.server_address[1]
        return server

    def request(self, method, path, body=None, port=None):
        conn = http.client.HTTPConnection("127.0.0.1", port or self.port, timeout=10)
        try:
            conn.request(method, path, body=body)
            resp = conn.getresponse()
            return resp.status, resp.headers, resp.read()
        finally:
            conn.close()

    def assert_healthy(self, path="/healthz"):
        status, headers, body = self.request("GET", path)
        self.assertEqual(status, 200, body)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(int(headers["Content-Length"]), len(body))
        body.decode("ascii")
        self.assertEqual(json.loads(body), {"status": "ok"})
        return headers, body


class HealthzTest(HealthzTestCase):
    def test_get(self):  # AC1
        self.start()
        _, body = self.assert_healthy()
        self.assertEqual(body, b'{"status": "ok"}')

    def test_head_same_headers_no_body(self):  # AC2
        self.start()
        get_headers, get_body = self.assert_healthy()
        status, headers, body = self.request("HEAD", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertEqual(headers["Content-Type"], get_headers["Content-Type"])
        self.assertEqual(headers["Content-Length"], str(len(get_body)))

    def test_query_string_ignored(self):
        self.start()
        for method in ("GET", "HEAD"):
            with self.subTest(method=method):
                plain = self.request(method, "/healthz")
                query = self.request(method, "/healthz?x=1")
                self.assertEqual(query[0], plain[0])
                self.assertEqual(query[2], plain[2])
                for name in ("Content-Type", "Content-Length"):
                    self.assertEqual(query[1][name], plain[1][name])

    def test_look_alikes_404(self):
        self.start()
        for path in LOOK_ALIKES:
            for method in ("GET", "HEAD"):
                with self.subTest(path=path, method=method):
                    status, headers, _ = self.request(method, path)
                    self.assertEqual(status, 404)
                    self.assertTrue(headers["Content-Type"].startswith("text/html"))

    def standard_501(self, method, path):
        """What the stock BaseHTTPRequestHandler answers for an unsupported method."""

        class Stock(serve.http.server.BaseHTTPRequestHandler):
            server_version = serve.RootOnlyHandler.server_version

            def log_message(self, *args):
                pass

        server = serve.http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stock)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            status, _, body = self.request(method, path, body=b"x", port=server.server_address[1])
            return status, body
        finally:
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()

    def test_other_methods_stock_501(self):
        self.start()
        for method in ("PUT", "DELETE", "POST"):
            with self.subTest(method=method):
                status, _, body = self.request(method, "/healthz", body=b"x")
                self.assertEqual(status, 501)
                self.assertEqual((status, body), self.standard_501(method, "/healthz"))

    def test_never_creates_store_file(self):
        self.start()
        self.assert_healthy()
        self.request("HEAD", "/healthz")
        self.assertFalse(os.path.exists(self.kv_path))

    def test_healthy_when_log_corrupt(self):
        with open(self.kv_path, "wb") as fh:
            fh.write(encode_record("set", "a", 1) + b"garbage\n" + encode_record("set", "b", 2))
        self.start()
        self.assertEqual(self.request("GET", "/kv/a")[0], 503)
        self.assert_healthy()
        self.assertEqual(self.request("HEAD", "/healthz")[0], 200)

    def test_healthy_when_store_unopenable(self):
        missing = os.path.join(self.tmp.name, "absent", "kv.log")
        self.use_kv_path(missing)
        self.start()
        self.assertEqual(self.request("GET", "/kv/a")[0], 500)
        self.assert_healthy()
        self.assertEqual(self.request("HEAD", "/healthz")[0], 200)
        self.assertFalse(os.path.exists(missing))

    def test_routes_table_unchanged(self):
        self.assertEqual(serve.ROUTES, {"/": serve.INDEX, "/jungle": serve.JUNGLE})


class HealthzDocsTest(unittest.TestCase):
    def test_docstring_documents_healthz(self):
        doc = serve.__doc__
        for needle in ("/healthz", '{"status": "ok"}', "/kv/", "KV_PATH", "./kv.log",
                       "python3 serve.py", "PORT=", "HOST="):
            self.assertIn(needle, doc)
        for banned in ("root-only", "exactly one document"):
            self.assertNotIn(banned, doc.lower())

    def test_readme_documents_healthz(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        for needle in ("## Health check (`/healthz`)", "curl -i http://127.0.0.1:8000/healthz",
                       '{"status": "ok"}', "application/json", "HEAD", "Authentication"):
            self.assertIn(needle, readme)


if __name__ == "__main__":
    unittest.main()
